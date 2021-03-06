"""Тесты для функций проверки необходимости обновления данных."""
from datetime import datetime, timezone

import pandas as pd
import pytest

from poptimizer.data.domain import services
from poptimizer.data.ports import outer

UTC_NOW = datetime.now(timezone.utc)
TO_NAIVE_CASES = (
    (
        UTC_NOW,
        UTC_NOW.replace(tzinfo=None),
    ),
    (
        datetime(2020, 9, 13, 13, 56, tzinfo=services.MOEX_TZ),
        datetime(2020, 9, 13, 10, 56),
    ),
)


@pytest.mark.parametrize("date, naive", TO_NAIVE_CASES)
def test_to_utc_naive(date, naive):
    """Корректность преобразования для UTC и Москвы."""
    utc_date = datetime.now(timezone.utc)
    assert services._to_utc_naive(utc_date) == utc_date.replace(tzinfo=None)


class FakeDateTime:
    """Возвращает текущее время в регионе биржи."""

    def __init__(self, date):
        """Сохраняет условное текущее время."""
        self.date = date

    def now(self, tzinfo):
        """Патч для текущего времени с указанной зоной."""
        return self.date.replace(tzinfo=tzinfo)


POTENTIAL_TRADING_DAY_CASES = (
    (
        datetime(2020, 9, 12, 0, 46),
        datetime(2020, 9, 11, 21, 45),
    ),
    (
        datetime(2020, 9, 12, 0, 44),
        datetime(2020, 9, 10, 21, 45),
    ),
)


@pytest.mark.parametrize("now, end", POTENTIAL_TRADING_DAY_CASES)
def test_trading_day_potential_end(now, end, monkeypatch):
    """Тестирование двух краевых случаев на стыке потенциального окончания торгового дня."""
    monkeypatch.setattr(services, "datetime", FakeDateTime(now))
    assert services.trading_day_potential_end() == end


def test_day_real_end():
    """Тест на окончание реального торгового дня."""
    df = pd.DataFrame([datetime(2020, 9, 11)], columns=["till"])
    assert services.trading_day_real_end(df) == datetime(2020, 9, 11, 21, 45)


MAIN_HELPER = outer.TableName(outer.TRADING_DATES, outer.TRADING_DATES)
HELPER_NAME_CASES = (
    (outer.TableName(outer.TRADING_DATES, outer.TRADING_DATES), None),
    (outer.TableName(outer.CONOMY, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.DOHOD, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.SMART_LAB, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.DIVIDENDS, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.CPI, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.SECURITIES, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.INDEX, outer.TRADING_DATES), MAIN_HELPER),
    (outer.TableName(outer.QUOTES, outer.TRADING_DATES), MAIN_HELPER),
)


@pytest.mark.parametrize("name, answer", HELPER_NAME_CASES)
def test_get_helper_name(name, answer):
    """Тесты для всех групп таблиц."""
    assert services.get_helper_name(name) == answer
