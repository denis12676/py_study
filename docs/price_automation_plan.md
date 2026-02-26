# План автоматизации управления ценами

## Что уже реализовано

- Ручное обновление цен (единично и массово) — `managers/products.py`
- UI для редактирования цен с пагинацией — `dashboard.py`
- NLP-команды типа "измени цену артикул 123 на 1500" — `ai_agent.py`
- API endpoints для цен подключены — `wb_client.py`

---

## Чего не хватает для автоматизации

### 1. Движок стратегий ценообразования

Сейчас нет никакой логики "при условии X — сделать Y". Нужен модуль `pricing_strategy.py`:

- **По остаткам**: мало товара → поднять цену, много → снизить
- **По конкурентам**: если конкурент дешевле → скорректировать (данные через WB или внешний API)
- **По маржинальности**: задать желаемую прибыль → автоматически рассчитать цену
- **По сезонности**: скидки в заданные периоды

### 2. Планировщик задач

Нет scheduled jobs — цены обновляются только вручную. Нужен **APScheduler** или аналог:

```python
# Пример: проверять цены каждые 4 часа
scheduler.add_job(auto_reprice, 'interval', hours=4)
```

### 3. Анализ эластичности и конверсии

- Не отслеживается, как изменение цены влияет на продажи
- Нет связки: `AnalyticsManager (продажи) → PricingStrategy (оптимум цены)`
- Нет расчёта RPM (revenue per mille) или profit margin per SKU

### 4. Журнал изменений цен

- Нет истории: "когда, на сколько и почему изменилась цена"
- Нет отката к предыдущей цене при ухудшении метрик

### 5. Правила и триггеры (Rules Engine)

```
Если: конверсия < 2% И остаток > 100 → скидка +5%
Если: остаток < 10               → цена +10%
Если: нет продаж 7 дней          → акция -15%
```

---

## Минимальный план реализации

| Приоритет | Компонент                              | Файл                              |
|-----------|----------------------------------------|-----------------------------------|
| 1         | Модель правил + стратегии              | `pricing_strategy.py`             |
| 2         | Подключение к аналитике (продажи/остатки) | расширить `managers/analytics.py` |
| 3         | Планировщик                            | `scheduler.py` + APScheduler      |
| 4         | История цен + откат                    | `price_history.py` или SQLite     |
| 5         | UI для настройки правил                | новая вкладка в `dashboard.py`    |

---

## Структура модулей (предлагаемая)

```
py_study-master/
├── pricing_strategy.py   — стратегии: MarginStrategy, StockStrategy, SeasonStrategy
├── price_history.py      — SQLite-журнал изменений + откат
├── scheduler.py          — APScheduler, запуск auto_reprice по расписанию
└── managers/
    └── analytics.py      — расширить: конверсия, эластичность, margin per SKU
```

---

## Пример архитектуры `pricing_strategy.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PriceRule:
    name: str
    condition: str   # "stock < 10", "conversion < 2", "no_sales_days > 7"
    action: str      # "price * 1.10", "discount + 5", "price * 0.85"
    enabled: bool = True

class PricingStrategy:
    def __init__(self, rules: list[PriceRule]):
        self.rules = rules

    def evaluate(self, product_data: dict) -> Optional[dict]:
        """
        Принимает данные по товару (цена, остаток, конверсия, дни без продаж),
        возвращает словарь с новой ценой/скидкой или None если изменений нет.
        """
        ...

class MarginStrategy(PricingStrategy):
    """Ценообразование на основе целевой маржи"""
    def __init__(self, target_margin: float, cost_price: float):
        ...

class StockStrategy(PricingStrategy):
    """Ценообразование на основе уровня остатков"""
    def __init__(self, low_stock_threshold: int, high_stock_threshold: int):
        ...
```

---

## Зависимости для установки

```bash
pip install apscheduler  # планировщик задач
```

SQLite уже входит в стандартную библиотеку Python — дополнительных зависимостей для журнала не нужно.
