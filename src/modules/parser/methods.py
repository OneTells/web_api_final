import re
from asyncio import new_event_loop, sleep, Runner
from contextlib import suppress
from signal import signal, SIGINT, SIG_IGN, SIGTERM, default_int_handler
from typing import Self

from bs4 import BeautifulSoup
from requests import Session
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.methods import async_engine
from core.model import Product
from modules.parser.schemes import ProductModel


# Класс Parser представляет собой парсер для извлечения данных из каталога на сайте maxidom.ru.
class Parser:

    def __init__(self):
        self.__session = Session()

    def close(self):
        self.__session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.close()

    def __parse_page(self, slug: str, page: int, amount: int = 30) -> tuple[bool, list[ProductModel]]:
        """
        Парсинг страницы каталога и извлечение данных о товарах

        :param slug: Уникальный идентификатор сегмента каталога
        :param page: Номер страницы
        :param amount: Количество товаров на странице
        :return: Список товаров страницы
        """

        response = self.__session.get(f'https://www.maxidom.ru/catalog/{slug}/?amount={amount}&PAGEN_2={page}')

        if response.status_code != 200:
            raise ValueError('Ошибка при запросе каталога. Повторите попытку')

        content = response.content

        soup = BeautifulSoup(content.decode(), 'html.parser')

        elements = (
            soup
            .find('div', {'class': 'lvl1__product-body lvl2 hidden lvl1__product-body-searchresult'})
            .find_all('article', {'class': 'l-product l-product__horizontal'})
        )

        page_data: list[ProductModel] = []

        for element in elements:
            name = element.find('span', {'itemprop': 'name'}).text
            product_path = element.find('a', {'itemprop': 'url'}).get('href')
            price = int(element.find('span', {'itemprop': 'price'}).text)

            page_data.append(ProductModel(name=name, url=f'https://www.maxidom.ru{product_path}', price=price))

        return not soup.find('a', {'id': 'navigation_2_next_page'}), page_data

    def parse_catalog(self, url: str) -> list[ProductModel]:
        """
        Парсинг каталога и извлечение данных о всех товарах в данном сегменте каталога

        :param url: Ссылка на сегмент каталога
        :return: Список товаров сегмента каталога
        """

        match = re.fullmatch(r'^https://www\.maxidom\.ru/catalog/([^/]+)/?', url)

        if not match:
            raise ValueError('Ссылка некорректна')

        slug = match.group(1)

        current_page = 1
        catalog_data: list[ProductModel] = []

        while True:
            is_last_page, page_data = self.__parse_page(slug, current_page)

            catalog_data += page_data

            if is_last_page:
                break

            current_page += 1

        return catalog_data


async def run_parser():
    async with async_sessionmaker(async_engine)() as session:
        with Parser() as parser:
            while True:
                result = parser.parse_catalog('https://www.maxidom.ru/catalog/tovary-dlya-poliva/')

                if result:
                    request = (
                        insert(Product)
                        .values([
                            {
                                'slug': product.url.removeprefix('https://www.maxidom.ru/catalog/').removesuffix('/'),
                                'name': product.name,
                                'price': product.price
                            } for product in result
                        ])
                    )

                    await session.execute(
                        request
                        .on_conflict_do_update(
                            index_elements=[Product.slug],
                            set_=dict(name=request.excluded.name, price=request.excluded.price)
                        )
                    )
                    await session.commit()

                await sleep(10)


def run_process():
    signal(SIGINT, SIG_IGN)
    signal(SIGTERM, default_int_handler)

    with suppress(KeyboardInterrupt):
        with Runner(loop_factory=new_event_loop) as runner:
            runner.run(run_parser())
