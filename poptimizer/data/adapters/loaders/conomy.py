"""Загрузка данных с https://www.conomy.ru/."""
from contextlib import asynccontextmanager
from typing import cast

import pandas as pd
import pyppeteer
from pyppeteer.browser import Browser
from pyppeteer.page import Page

from poptimizer.data.adapters import logger
from poptimizer.data.adapters.html import description, parser
from poptimizer.data.ports import col, outer

# Параметры поиска страницы эмитента
SEARCH_URL = "https://www.conomy.ru/search"
SEARCH_FIELD = '//*[@id="issuer_search"]'

# Параметры поиска данных по дивидендам
DIVIDENDS_MENU = '//*[@id="page-wrapper"]/div/nav/ul/li[5]/a'
DIVIDENDS_TABLE = '//*[@id="page-container"]/div[2]/div/div[1]'

# Номер таблицы на html-странице и строки с заголовком
TABLE_INDEX = 1

# Параметры проверки обыкновенная акция или привилегированная
COMMON_TICKER_LENGTH = 4
PREFERRED_TICKER_ENDING = "P"


@asynccontextmanager
async def _get_browser() -> Browser:
    """Асинхронный браузер с автоматическим закрытием после использования."""
    browser = await pyppeteer.launch()
    try:
        yield browser
    finally:
        await browser.close()


async def _load_ticker_page(page: Page, ticker: str) -> None:
    """Вводит в поле поиска тикер и переходит на страницу с информацией по эмитенту."""
    await page.goto(SEARCH_URL)
    await page.waitForXPath(SEARCH_FIELD)
    element, *_ = await page.xpath(SEARCH_FIELD)
    await element.type(ticker)
    await element.press("Enter")


async def _load_dividends_table(page: Page) -> None:
    """Выбирает на странице эмитента меню дивиденды и дожидается загрузки таблиц с ними."""
    await page.waitForXPath(DIVIDENDS_MENU)
    element, *_ = await page.xpath(DIVIDENDS_MENU)
    await element.click()
    await page.waitForXPath(DIVIDENDS_TABLE)


async def _get_html(ticker: str) -> str:
    """Возвращает html-код страницы с данными по дивидендам с сайта https://www.conomy.ru/."""
    async with _get_browser() as browser:
        page = await browser.newPage()
        await _load_ticker_page(page, ticker)
        await _load_dividends_table(page)
        html = await page.content()
        return cast(str, html)


def _is_common(ticker: str) -> bool:
    """Определяет является ли акция обыкновенной."""
    if len(ticker) == COMMON_TICKER_LENGTH:
        return True
    elif len(ticker) == COMMON_TICKER_LENGTH + 1:
        if ticker[COMMON_TICKER_LENGTH] == PREFERRED_TICKER_ENDING:
            return False
    raise outer.DataError(f"Некорректный тикер {ticker}")


def _get_col_desc(ticker: str) -> parser.Descriptions:
    """Формирует список с описанием необходимых столбцов."""
    date = description.ColDesc(
        num=5,
        raw_name=("E", "Дата закрытия реестра акционеров", "Под выплату дивидендов"),
        name=col.DATE,
        parser_func=description.date_parser,
    )
    columns = [date]

    if _is_common(ticker):
        common = description.ColDesc(
            num=7,
            raw_name=("G", "Размер дивидендов", "АОИ"),
            name=ticker,
            parser_func=description.div_parser,
        )
        columns.append(common)
        return columns

    preferred = description.ColDesc(
        num=8,
        raw_name=("H", "Размер дивидендов", "АПИ"),
        name=ticker,
        parser_func=description.div_parser,
    )
    columns.append(preferred)
    return columns


class ConomyLoader(logger.LoaderLoggerMixin, outer.AbstractLoader):
    """Обновление для таблиц с дивидендами на https://www.conomy.ru/."""

    async def get(self, table_name: outer.TableName) -> pd.DataFrame:
        """Получение дивидендов для заданного тикера."""
        ticker = self._log_and_validate_group(table_name, outer.CONOMY)

        html = await _get_html(ticker)
        cols_desc = _get_col_desc(ticker)
        df = parser.get_df_from_html(html, TABLE_INDEX, cols_desc)
        df = df.dropna()
        df = df.sort_index(axis=0)
        return df.groupby(lambda date: date).sum()
