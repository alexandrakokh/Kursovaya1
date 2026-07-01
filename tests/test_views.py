import pytest
import pandas as pd
from datetime import datetime
from src.views import get_greeting, build_main_page_response


@pytest.fixture
def mock_currency_and_stock():
    """Единая фикстура для валют и акций (формат строго по чек-листу)."""
    return {
        "currency_rates": [
            {"currency": "USD", "rate": 90.0},
            {"currency": "EUR", "rate": 100.0}
        ],
        "stock_prices": [
            {"stock": "AAPL", "price": 150.0},
            {"stock": "GOOGL", "price": 140.0}
        ]
    }


@pytest.fixture
def empty_df():
    return pd.DataFrame()


@pytest.fixture
def sample_transactions():
    """Минимальный пример данных (4 строки) для быстрых тестов."""
    data = {
        "Дата операции": [
            datetime(2023, 10, 1, 10, 0),
            datetime(2023, 10, 2, 14, 0),
            datetime(2023, 10, 3, 19, 0),
            datetime(2023, 10, 4, 12, 0),
        ],
        "Номер карты": ["1234", "1234", "5678", "5678"],
        "Сумма операции": [-1000, -2000, 500, -3000],
        "Категория": ["Продукты", "Переводы", "Продукты", "Одежда"],
        "Описание": ["Молоко", "Перевод другу", "Хлеб", "Куртка"]
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_transactions_rich():
    """
    Расширенный набор данных: много категорий, много транзакций.
    Нужен, чтобы реально проверить топ-5, топ-7 и «Остальное».
    """
    categories = [
        "Продукты", "Такси", "Одежда", "Развлечения", "Техника",
        "Книги", "Спорт", "Переводы", "Наличные", "Другое", "Кафе"
    ]
    amounts = [-1000, -900, -800, -700, -600, -500, -400, -3000, -2000, -100, -150]
    cards = ["1112"] * len(categories)

    data = {
        "Дата операции": [datetime(2023, 10, i, 10, 0) for i in range(1, len(categories) + 1)],
        "Номер карты": cards,
        "Сумма операции": amounts,
        "Категория": categories,
        "Описание": [f"Покупка {i}" for i in range(len(categories))]
    }
    return pd.DataFrame(data)


class TestGetGreeting:
    """Тесты для функции приветствия по времени."""

    @pytest.mark.parametrize("hour, expected", [
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
        (0, "Доброй ночи"),
        (5, "Доброй ночи"),
    ])
    def test_greeting_by_hour(self, hour, expected):
        dt = datetime(2023, 1, 1, hour=hour, minute=30)
        assert get_greeting(dt) == expected


class TestBuildMainPageResponse:
    """Тесты для главной страницы."""

    def test_empty_dataframe(self, mock_currency_and_stock, empty_df):
        response = build_main_page_response(
            transactions=empty_df,
            report_date_str="2023-10-01 12:00:00",  # исправлено имя аргумента
            now=datetime.now(),                    # добавлен обязательный аргумент
            **mock_currency_and_stock
        )
        # Приветствие зависит от текущего времени, поэтому не проверяем точное значение, только наличие
        assert "greeting" in response
        assert response["cards"] == []
        assert response["top_categories"] == []
        assert response["total_operations_count"] == 0

    def test_no_amount_column(self, mock_currency_and_stock):
        df = pd.DataFrame({
            "Дата операции": [datetime.now()],
            "Номер карты": ["1234"],
            "Категория": ["Еда"]
            # Сумма операции отсутствует специально
        })
        response = build_main_page_response(
            transactions=df,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )
        assert isinstance(response, dict)
        assert "total_operations_count" in response
        # Если нет суммы, то по карте трат не будет
        assert len(response["cards"]) == 0

    def test_cards_calculation(self, mock_currency_and_stock, sample_transactions):
        response = build_main_page_response(
            transactions=sample_transactions,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )

        assert len(response["cards"]) >= 1
        card_1234 = next((c for c in response["cards"] if c["last_digits"] == "1234"), None)
        if card_1234:
            # Траты: -1000 (Продукты) + -2000 (Переводы) = -3000. Кешбэк = 30.
            assert card_1234["total_spent"] == -3000
            assert card_1234["cashback"] == 30

    def test_top_transactions_exclude_transfers(self, mock_currency_and_stock, sample_transactions):
        response = build_main_page_response(
            transactions=sample_transactions,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )

        top_cats = [t.get("category") for t in response["top_transactions"]]
        assert "Переводы" not in top_cats
        assert len(response["top_transactions"]) <= 5

    def test_top_categories_special_handling(self, mock_currency_and_stock, sample_transactions_rich):
        response = build_main_page_response(
            transactions=sample_transactions_rich,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )

        top_cats_names = [c["category"] for c in response["top_categories"]]
        # Спецкатегории должны быть в списке
        assert "Переводы" in top_cats_names
        assert "Наличные" in top_cats_names

        # Проверяем, что есть «Остальное» (так как категорий много)
        has_rest = any(c["category"] == "Остальное" for c in response["top_categories"])
        assert has_rest, "Должно быть поле «Остальное», так как категорий больше 7"

    def test_cashback_categories_exclude_special(self, mock_currency_and_stock, sample_transactions):
        response = build_main_page_response(
            transactions=sample_transactions,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )

        cb_cats = [c["category"] for c in response["top_cashback_categories"]]
        assert "Переводы" not in cb_cats

    def test_invalid_date_string_fallback(self, mock_currency_and_stock, sample_transactions):
        response = build_main_page_response(
            transactions=sample_transactions,
            report_date_str="НЕ_ДАТА",
            now=datetime.now(),
            **mock_currency_and_stock
        )
        greeting = response["greeting"]
        assert greeting in ["Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи"]

    def test_top_transactions_date_format(self, mock_currency_and_stock, sample_transactions_rich):
        response = build_main_page_response(
            transactions=sample_transactions_rich,
            report_date_str="2023-10-01 12:00:00",
            now=datetime.now(),
            **mock_currency_and_stock
        )

        top_transactions = response["top_transactions"]
        assert len(top_transactions) > 0, "Топ-транзакций нет, тест не имеет смысла"

        # Должно быть ровно 5 записей
        assert len(top_transactions) == 5, f"Должно быть ровно 5 транзакций, а получено {len(top_transactions)}"

        for t in top_transactions:
            assert isinstance(t["date"], str), f"Дата не строка: {t['date']!r}"
            parts = t["date"].split(".")
            assert len(parts) == 3, f"Неверный формат даты (нет трёх частей): {t['date']}"
            day, month, year = parts
            assert len(day) == 2, f"День должен быть 2 символа: {day}"
            assert len(month) == 2, f"Месяц должен быть 2 символа: {month}"
            assert len(year) == 4, f"Год должен быть 4 символа: {year}"
