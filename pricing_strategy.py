"""
pricing_strategy.py — движок автоматического ценообразования.

Архитектура:
  PricingContext   — снимок данных по одному товару (цена, остаток, продажи)
  PriceAction      — решение: новая цена + причина
  PricingStrategy  — базовый класс стратегии
  StockStrategy    — цена на основе уровня остатков
  ConversionStrategy — цена на основе скорости продаж / дней без продаж
  MarginStrategy   — цена на основе целевой маржи (нужна себестоимость)
  SeasonStrategy   — скидка / наценка в заданный период дат
  PricingEngine    — оркестратор: собирает данные, оценивает стратегии, применяет цены

Использование:
    from pricing_strategy import PricingEngine, StockStrategy, ConversionStrategy

    engine = PricingEngine(
        products_mgr=agent.products,
        analytics_mgr=agent.analytics,
        inventory_mgr=agent.inventory,
        strategies=[
            StockStrategy(low_threshold=10, low_markup=0.10, high_threshold=200, high_discount=5),
            ConversionStrategy(no_sales_days=7, discount_delta=5, max_discount=50),
        ]
    )

    actions = engine.run(dry_run=True)   # проверить без применения
    actions = engine.run(dry_run=False)  # применить реально
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Контекст и действие
# ---------------------------------------------------------------------------

@dataclass
class PricingContext:
    """Снимок данных по одному товару для оценки стратегий."""
    nm_id: int
    vendor_code: str
    title: str
    current_price: float          # цена без скидки (розничная)
    current_discount: int         # текущая скидка в %
    stock_total: int              # суммарный остаток FBO + FBS
    avg_daily_orders: float       # среднее число заказов в день за 30 дней
    days_without_sales: int       # дней подряд без продаж
    revenue_30d: float            # выручка за 30 дней, руб.

    @property
    def discounted_price(self) -> float:
        """Цена покупателя после скидки."""
        return round(self.current_price * (1 - self.current_discount / 100), 2)

    @property
    def days_of_stock(self) -> float:
        """
        Оборачиваемость: сколько дней хватит текущего запаса при текущей скорости продаж.

        Примеры:
          stock=100, avg_daily_orders=10  → 10 дней  (дефицит)
          stock=100, avg_daily_orders=0.5 → 200 дней (затоваривание)
          stock=0                         → 0 дней
          stock>0, avg_daily_orders=0     → inf (нет продаж, склад стоит)
        """
        if self.stock_total <= 0:
            return 0.0
        if self.avg_daily_orders <= 0:
            return float("inf")
        return round(self.stock_total / self.avg_daily_orders, 1)


@dataclass
class PriceAction:
    """Решение об изменении цены для одного товара."""
    nm_id: int
    vendor_code: str
    title: str
    old_price: float
    old_discount: int
    new_price: float
    new_discount: int
    reason: str
    strategy_name: str
    applied: bool = False         # True после фактической отправки в API


# ---------------------------------------------------------------------------
# Базовый класс стратегии
# ---------------------------------------------------------------------------

class PricingStrategy(ABC):
    """
    Базовый класс. Каждая стратегия принимает PricingContext
    и возвращает PriceAction или None (если изменений не нужно).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Название стратегии для логов."""
        ...

    @abstractmethod
    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        """
        Оценить контекст и предложить изменение цены.

        Returns:
            PriceAction — если нужно изменить цену.
            None — если текущая цена оптимальна.
        """
        ...

    def _make_action(
        self,
        ctx: PricingContext,
        new_price: float,
        new_discount: int,
        reason: str,
    ) -> Optional[PriceAction]:
        """Вспомогательный метод: создать PriceAction только если цена/скидка изменились."""
        new_price = round(new_price)
        new_discount = max(0, min(95, new_discount))  # WB ограничение: 0–95%

        if new_price == round(ctx.current_price) and new_discount == ctx.current_discount:
            return None

        return PriceAction(
            nm_id=ctx.nm_id,
            vendor_code=ctx.vendor_code,
            title=ctx.title,
            old_price=ctx.current_price,
            old_discount=ctx.current_discount,
            new_price=new_price,
            new_discount=new_discount,
            reason=reason,
            strategy_name=self.name,
        )


# ---------------------------------------------------------------------------
# Стратегия 1: По уровню остатков
# ---------------------------------------------------------------------------

class StockStrategy(PricingStrategy):
    """
    Управление ценой в зависимости от остатка FBO:

      - Мало товара (< low_threshold)  → наценка на low_markup %
      - Много товара (> high_threshold) → скидка на high_discount %

    Пример:
        StockStrategy(low_threshold=10, low_markup=0.10,
                      high_threshold=200, high_discount=5)
        При остатке < 10 шт: цена × 1.10
        При остатке > 200 шт: скидка +5%
    """

    def __init__(
        self,
        low_threshold: int = 10,
        low_markup: float = 0.10,
        high_threshold: int = 150,
        high_discount: int = 5,
    ):
        self.low_threshold = low_threshold
        self.low_markup = low_markup          # доля: 0.10 = +10%
        self.high_threshold = high_threshold
        self.high_discount = high_discount    # процент скидки: 5 = 5%

    @property
    def name(self) -> str:
        return "StockStrategy"

    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        if ctx.stock_total < self.low_threshold:
            new_price = ctx.current_price * (1 + self.low_markup)
            reason = (
                f"Остаток FBO+FBS {ctx.stock_total} шт < {self.low_threshold} шт → "
                f"наценка +{int(self.low_markup * 100)}%"
            )
            return self._make_action(ctx, new_price, ctx.current_discount, reason)

        if ctx.stock_total > self.high_threshold:
            new_discount = ctx.current_discount + self.high_discount
            reason = (
                f"Остаток FBO+FBS {ctx.stock_total} шт > {self.high_threshold} шт → "
                f"скидка +{self.high_discount}%"
            )
            return self._make_action(ctx, ctx.current_price, new_discount, reason)

        return None


# ---------------------------------------------------------------------------
# Стратегия 2: По оборачиваемости (скорость заказов × остаток)
# ---------------------------------------------------------------------------

class TurnoverStrategy(PricingStrategy):
    """
    Ценообразование на основе оборачиваемости склада.

    Оборачиваемость = stock_total / avg_daily_orders (дней запаса).

    Логика:
      - Мало дней запаса (< understock_days) → товар разбирают быстро,
        поднять цену на markup %
      - Много дней запаса (> overstock_days) → товар залёживается,
        добавить скидку на discount_delta %

    Почему лучше чистого остатка:
      100 шт при 10 заказов/день = 10 дней → нужно поднять цену
      100 шт при 0.5 заказа/день = 200 дней → нужна скидка
      10 шт при 0.1 заказа/день  = 100 дней → цену трогать не нужно

    Пример:
        TurnoverStrategy(understock_days=7,  markup=0.10,
                         overstock_days=60,  discount_delta=7)
    """

    def __init__(
        self,
        understock_days: int = 7,
        markup: float = 0.10,
        overstock_days: int = 60,
        discount_delta: int = 7,
        max_discount: int = 60,
    ):
        self.understock_days = understock_days
        self.markup          = markup
        self.overstock_days  = overstock_days
        self.discount_delta  = discount_delta
        self.max_discount    = max_discount

    @property
    def name(self) -> str:
        return "TurnoverStrategy"

    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        days = ctx.days_of_stock

        if days == 0:
            return None  # нет товара — не трогаем цену

        if days < self.understock_days:
            new_price = ctx.current_price * (1 + self.markup)
            reason = (
                f"Запас на {days:.1f} дн < {self.understock_days} дн "
                f"({ctx.stock_total} шт / {ctx.avg_daily_orders:.1f} зак/день) → "
                f"наценка +{int(self.markup * 100)}%"
            )
            return self._make_action(ctx, new_price, ctx.current_discount, reason)

        if days > self.overstock_days:
            new_discount = min(ctx.current_discount + self.discount_delta, self.max_discount)
            reason = (
                f"Запас на {days:.1f} дн > {self.overstock_days} дн "
                f"({ctx.stock_total} шт / {ctx.avg_daily_orders:.1f} зак/день) → "
                f"скидка +{self.discount_delta}%"
            )
            return self._make_action(ctx, ctx.current_price, new_discount, reason)

        return None


# ---------------------------------------------------------------------------
# Стратегия 3: По скорости продаж / дням без продаж
# ---------------------------------------------------------------------------

class ConversionStrategy(PricingStrategy):
    """
    Управление ценой на основе активности продаж:

      - Нет продаж N дней → снизить скидку на discount_delta %
      - Высокая скорость продаж (avg_daily_orders > fast_threshold) → поднять цену

    Пример:
        ConversionStrategy(no_sales_days=7, discount_delta=5, max_discount=50,
                           fast_threshold=5.0, fast_markup=0.05)
        Нет продаж 7 дней → скидка +5% (но не более 50%)
        > 5 заказов/день → цена +5%
    """

    def __init__(
        self,
        no_sales_days: int = 7,
        discount_delta: int = 5,
        max_discount: int = 50,
        fast_threshold: float = 5.0,
        fast_markup: float = 0.05,
    ):
        self.no_sales_days = no_sales_days
        self.discount_delta = discount_delta
        self.max_discount = max_discount
        self.fast_threshold = fast_threshold
        self.fast_markup = fast_markup

    @property
    def name(self) -> str:
        return "ConversionStrategy"

    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        if ctx.days_without_sales >= self.no_sales_days and ctx.stock_total > 0:
            new_discount = min(ctx.current_discount + self.discount_delta, self.max_discount)
            reason = (
                f"Нет продаж {ctx.days_without_sales} дней → "
                f"скидка +{self.discount_delta}% (итого {new_discount}%)"
            )
            return self._make_action(ctx, ctx.current_price, new_discount, reason)

        if ctx.avg_daily_orders >= self.fast_threshold:
            new_price = ctx.current_price * (1 + self.fast_markup)
            reason = (
                f"Высокий спрос: {ctx.avg_daily_orders:.1f} заказов/день → "
                f"наценка +{int(self.fast_markup * 100)}%"
            )
            return self._make_action(ctx, new_price, ctx.current_discount, reason)

        return None


# ---------------------------------------------------------------------------
# Стратегия 3: По целевой марже
# ---------------------------------------------------------------------------

class MarginStrategy(PricingStrategy):
    """
    Устанавливает цену так, чтобы обеспечить целевую маржу после комиссии WB.

    Формула: price = cost_price / (1 - target_margin - wb_commission)
    Если рассчитанная цена выше/ниже текущей на tolerance — обновить.

    Пример:
        MarginStrategy(
            cost_prices={123456: 500, 789012: 300},  # себестоимость по nmID
            target_margin=0.25,   # 25% маржи
            wb_commission=0.15,   # 15% комиссия WB
            tolerance=0.05        # менять цену только если отклонение > 5%
        )
    """

    def __init__(
        self,
        cost_prices: Dict[int, float],
        target_margin: float = 0.20,
        wb_commission: float = 0.15,
        tolerance: float = 0.05,
    ):
        self.cost_prices = cost_prices
        self.target_margin = target_margin
        self.wb_commission = wb_commission
        self.tolerance = tolerance

    @property
    def name(self) -> str:
        return "MarginStrategy"

    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        cost = self.cost_prices.get(ctx.nm_id)
        if cost is None:
            return None  # нет данных о себестоимости — пропускаем

        denominator = 1 - self.target_margin - self.wb_commission
        if denominator <= 0:
            logger.warning(
                "MarginStrategy: некорректные параметры для nmID %d "
                "(target_margin=%.2f, wb_commission=%.2f)",
                ctx.nm_id, self.target_margin, self.wb_commission,
            )
            return None

        target_price = cost / denominator
        deviation = abs(target_price - ctx.current_price) / ctx.current_price

        if deviation > self.tolerance:
            reason = (
                f"Себестоимость {cost} руб, целевая маржа {int(self.target_margin * 100)}% → "
                f"целевая цена {round(target_price)} руб "
                f"(отклонение {int(deviation * 100)}%)"
            )
            return self._make_action(ctx, target_price, ctx.current_discount, reason)

        return None


# ---------------------------------------------------------------------------
# Стратегия 4: Сезонная / по дате
# ---------------------------------------------------------------------------

@dataclass
class SeasonPeriod:
    """Один сезонный период: диапазон дат и действие."""
    name: str
    date_from: str          # "MM-DD", например "11-20"
    date_to: str            # "MM-DD", например "12-05"
    discount_add: int = 0   # добавить % скидки (положительное = скидка)
    price_mult: float = 1.0 # умножить цену (1.1 = +10%, 0.9 = −10%)


class SeasonStrategy(PricingStrategy):
    """
    Применяет ценовые изменения в заданные периоды (например, распродажи WB).

    Пример:
        SeasonStrategy(periods=[
            SeasonPeriod("Чёрная пятница", "11-20", "12-05", discount_add=10),
            SeasonPeriod("Новый год",       "12-20", "01-05", discount_add=15),
            SeasonPeriod("Вне сезона",      "02-01", "03-15", price_mult=1.10),
        ])
    """

    def __init__(self, periods: List[SeasonPeriod]):
        self.periods = periods

    @property
    def name(self) -> str:
        return "SeasonStrategy"

    def _is_active(self, period: SeasonPeriod) -> bool:
        """Проверить, активен ли период сегодня (поддерживает переход через год)."""
        today = datetime.now()
        year = today.year
        fmt = "%Y-%m-%d"

        try:
            d_from = datetime.strptime(f"{year}-{period.date_from}", fmt)
            d_to   = datetime.strptime(f"{year}-{period.date_to}",   fmt)
        except ValueError:
            logger.warning("SeasonStrategy: неверный формат даты в периоде '%s'", period.name)
            return False

        if d_from <= d_to:
            return d_from <= today <= d_to
        else:
            # переход через год: например 12-20 → 01-05
            return today >= d_from or today <= d_to

    def evaluate(self, ctx: PricingContext) -> Optional[PriceAction]:
        for period in self.periods:
            if not self._is_active(period):
                continue

            new_price    = ctx.current_price * period.price_mult
            new_discount = ctx.current_discount + period.discount_add
            reason = f"Сезонный период «{period.name}»"
            action = self._make_action(ctx, new_price, new_discount, reason)
            if action:
                return action  # применяем первый подходящий период

        return None


# ---------------------------------------------------------------------------
# Оркестратор
# ---------------------------------------------------------------------------

class PricingEngine:
    """
    Собирает данные по всем товарам, применяет стратегии, отправляет изменения в API.

    Args:
        products_mgr:  ProductsManager (для получения цен и обновления)
        analytics_mgr: AnalyticsManager (для продаж и скорости заказов)
        inventory_mgr: InventoryManager (для остатков FBO + FBS)
        strategies:    Список стратегий в порядке приоритета.
                       Применяется первая стратегия, вернувшая действие.
        analytics_days: Горизонт анализа продаж (по умолчанию 30 дней)
    """

    def __init__(
        self,
        products_mgr,
        analytics_mgr,
        inventory_mgr,
        strategies: List[PricingStrategy],
        analytics_days: int = 30,
    ):
        self.products   = products_mgr
        self.analytics  = analytics_mgr
        self.inventory  = inventory_mgr
        self.strategies = strategies
        self.analytics_days = analytics_days

    # ------------------------------------------------------------------
    # Сбор данных
    # ------------------------------------------------------------------

    def _build_contexts(self) -> List[PricingContext]:
        """Собрать PricingContext для каждого товара."""
        logger.info("PricingEngine: сбор данных...")

        # 1. Товары с ценами
        goods = self.products.get_products_with_prices(limit=1000)
        if not goods:
            logger.warning("PricingEngine: список товаров пуст")
            return []

        nm_ids = [g["nmID"] for g in goods]

        # 2. Суммарные остатки FBO + FBS: {nmId: quantity}
        fbo_stocks = self._get_fbo_stocks_map()
        fbs_stocks = self._get_fbs_stocks_map()
        total_stocks = {
            nm_id: fbo_stocks.get(nm_id, 0) + fbs_stocks.get(nm_id, 0)
            for nm_id in set(fbo_stocks) | set(fbs_stocks)
        }

        # 3. Скорость заказов: {nm_id: avg_daily_orders}
        avg_orders_map: Dict[int, float] = {}
        try:
            avg_orders_map = self.analytics.get_avg_orders_by_nm_ids(
                nm_ids, days=self.analytics_days
            )
        except Exception as e:
            logger.warning("PricingEngine: не удалось получить скорость заказов: %s", e)

        # 4. Дни без продаж: {nm_id: days}
        days_without_sales = self._calc_days_without_sales(nm_ids)

        # 5. Выручка за 30 дней: {nm_id: revenue}
        revenue_map = self._calc_revenue_map(nm_ids)

        # Сборка контекстов
        contexts: List[PricingContext] = []
        for g in goods:
            nm_id    = g["nmID"]
            sizes    = g.get("sizes", [])
            price    = sizes[0].get("price", 0) if sizes else 0
            discount = g.get("discount", 0)

            ctx = PricingContext(
                nm_id=nm_id,
                vendor_code=g.get("vendorCode", ""),
                title=g.get("subjectName", g.get("vendorCode", str(nm_id))),
                current_price=float(price),
                current_discount=int(discount),
                stock_total=total_stocks.get(nm_id, 0),
                avg_daily_orders=float(avg_orders_map.get(nm_id, 0)),
                days_without_sales=days_without_sales.get(nm_id, 0),
                revenue_30d=revenue_map.get(nm_id, 0.0),
            )
            contexts.append(ctx)

        logger.info("PricingEngine: построено %d контекстов", len(contexts))
        return contexts

    def _get_fbo_stocks_map(self) -> Dict[int, int]:
        """Остатки FBO (склад WB): {nmId: quantity}."""
        result: Dict[int, int] = {}
        try:
            stocks = self.inventory.get_fbo_stocks()
            for s in stocks:
                nm_id = s.get("nmId")
                qty   = s.get("quantity") or s.get("stockCount") or 0
                if nm_id:
                    result[int(nm_id)] = result.get(int(nm_id), 0) + int(qty)
        except Exception as e:
            logger.warning("PricingEngine: ошибка получения FBO остатков: %s", e)
        return result

    def _get_fbs_stocks_map(self) -> Dict[int, int]:
        """Остатки FBS (склад продавца) по всем складам: {nmId: quantity}."""
        result: Dict[int, int] = {}
        try:
            all_wh = self.inventory.get_all_fbs_stocks()  # {warehouse_id: [stocks]}
            for stocks in all_wh.values():
                for s in stocks:
                    nm_id = s.get("nmId")
                    qty   = s.get("amount", 0)
                    if nm_id:
                        result[int(nm_id)] = result.get(int(nm_id), 0) + int(qty)
        except Exception as e:
            logger.warning("PricingEngine: ошибка получения FBS остатков: %s", e)
        return result

    def _calc_days_without_sales(self, nm_ids: List[int]) -> Dict[int, int]:
        """
        Для каждого товара — сколько дней подряд нет продаж.
        Берём продажи за 30 дней и смотрим, когда была последняя.
        """
        result: Dict[int, int] = {nm: 0 for nm in nm_ids}
        try:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            sales = self.analytics.get_sales(date_from=date_from)
            last_sale_date: Dict[int, datetime] = {}

            for sale in sales:
                if sale.get("isCancel") or sale.get("isReturn"):
                    continue
                nm_id = sale.get("nmId")
                if nm_id is None:
                    continue
                nm_id = int(nm_id)
                raw_date = sale.get("date", "")[:10]
                try:
                    sale_dt = datetime.strptime(raw_date, "%Y-%m-%d")
                except ValueError:
                    continue
                if nm_id not in last_sale_date or sale_dt > last_sale_date[nm_id]:
                    last_sale_date[nm_id] = sale_dt

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for nm_id in nm_ids:
                last = last_sale_date.get(nm_id)
                result[nm_id] = (today - last).days if last else 30  # нет продаж = 30 дней
        except Exception as e:
            logger.warning("PricingEngine: ошибка расчёта дней без продаж: %s", e)
        return result

    def _calc_revenue_map(self, nm_ids: List[int]) -> Dict[int, float]:
        """Выручка по nmId за 30 дней."""
        result: Dict[int, float] = {nm: 0.0 for nm in nm_ids}
        try:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            sales = self.analytics.get_sales(date_from=date_from)
            for sale in sales:
                if sale.get("isCancel") or sale.get("isReturn"):
                    continue
                nm_id = sale.get("nmId")
                if nm_id is None:
                    continue
                result[int(nm_id)] = result.get(int(nm_id), 0.0) + float(sale.get("forPay", 0) or 0)
        except Exception as e:
            logger.warning("PricingEngine: ошибка расчёта выручки: %s", e)
        return result

    # ------------------------------------------------------------------
    # Оценка стратегий
    # ------------------------------------------------------------------

    def _evaluate(self, contexts: List[PricingContext]) -> List[PriceAction]:
        """Применить стратегии к каждому контексту, вернуть список действий."""
        actions: List[PriceAction] = []
        for ctx in contexts:
            if ctx.current_price <= 0:
                continue
            for strategy in self.strategies:
                action = strategy.evaluate(ctx)
                if action:
                    logger.debug(
                        "[%s] nmID=%d %s: %s → цена %d (скидка %d%%)",
                        action.strategy_name, ctx.nm_id, ctx.vendor_code,
                        action.reason, action.new_price, action.new_discount,
                    )
                    actions.append(action)
                    break  # первая сработавшая стратегия побеждает
        return actions

    # ------------------------------------------------------------------
    # Применение
    # ------------------------------------------------------------------

    def _apply(self, actions: List[PriceAction]) -> None:
        """Отправить изменения цен в API пачками по 1000."""
        if not actions:
            return

        payload = [
            {"nmID": a.nm_id, "price": int(a.new_price), "discount": a.new_discount}
            for a in actions
        ]

        batch_size = 1000
        for i in range(0, len(payload), batch_size):
            batch = payload[i:i + batch_size]
            try:
                result = self.products.update_multiple_prices(batch)
                upload_id = result.get("data", {}).get("uploadID", "?")
                logger.info(
                    "PricingEngine: отправлено %d изменений цен, uploadID=%s",
                    len(batch), upload_id,
                )
                # отмечаем успешно применённые
                for a in actions[i:i + batch_size]:
                    a.applied = True
            except Exception as e:
                logger.error("PricingEngine: ошибка применения цен: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # Основной метод
    # ------------------------------------------------------------------

    def run(self, dry_run: bool = True) -> List[PriceAction]:
        """
        Запустить цикл переоценки.

        Args:
            dry_run: True — только рассчитать, не отправлять в API.
                     False — рассчитать И применить изменения.

        Returns:
            Список PriceAction с предложенными / применёнными изменениями.
        """
        logger.info("PricingEngine.run(dry_run=%s) — стратегии: %s",
                    dry_run, [s.name for s in self.strategies])

        contexts = self._build_contexts()
        if not contexts:
            logger.warning("PricingEngine: нет товаров для переоценки")
            return []

        actions = self._evaluate(contexts)
        logger.info("PricingEngine: %d товаров требуют изменения цены", len(actions))

        if not dry_run:
            self._apply(actions)

        return actions

    def summary(self, actions: List[PriceAction]) -> str:
        """Текстовый отчёт по результатам run()."""
        if not actions:
            return "Изменений цен не требуется."

        lines = [f"Рекомендации по ценам ({len(actions)} товаров):\n"]
        for a in actions:
            status = "✅ применено" if a.applied else "📋 рекомендация"
            lines.append(
                f"  {status} | {a.vendor_code} (nmID {a.nm_id})\n"
                f"    Цена: {a.old_price:.0f} → {a.new_price:.0f} руб | "
                f"Скидка: {a.old_discount}% → {a.new_discount}%\n"
                f"    Причина: {a.reason}\n"
                f"    Стратегия: {a.strategy_name}\n"
            )
        return "\n".join(lines)
