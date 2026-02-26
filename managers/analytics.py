"""
AnalyticsManager — аналитика продаж и отчеты.
Продажи, заказы, детальный отчет, топ товаров, еженедельный отчет.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from wb_client import WildberriesAPI, API_ENDPOINTS
from cache import APICache

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Аналитика продаж и отчеты"""

    def __init__(self, api: WildberriesAPI):
        self.api = api
        self._cache = APICache(ttl=600)  # 10 минут
        self._last_api_call: float = 0.0

    def _wait_between_calls(self, min_interval: float = 1.0):
        """Ожидание между API вызовами для предотвращения 429"""
        current_time = time.time()
        elapsed = current_time - self._last_api_call
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_api_call = time.time()

    def clear_cache(self):
        """Очистить кэш"""
        self._cache.clear()

    @staticmethod
    def _to_int_nm_id(value: Any) -> Optional[int]:
        """Normalize nmID/nmId that can come as int/float/string."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value.is_integer():
                return int(value)
            return None

        text = str(value).strip()
        if not text:
            return None

        # Accept formats like "12345" and "12345.0", reject non-integer ids.
        try:
            numeric = float(text)
        except ValueError:
            return None
        if numeric.is_integer():
            return int(numeric)
        return None


    @classmethod
    def _normalize_avg_orders_map(cls, raw_map: Any) -> Dict[int, float]:
        """Convert cached JSON map keys back to int nmIDs."""
        if not isinstance(raw_map, dict):
            return {}

        normalized: Dict[int, float] = {}
        for raw_key, raw_value in raw_map.items():
            nm_id = cls._to_int_nm_id(raw_key)
            if nm_id is None:
                continue
            try:
                normalized[nm_id] = float(raw_value or 0)
            except (TypeError, ValueError):
                normalized[nm_id] = 0.0
        return normalized

    def get_sales(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить отчет о продажах.

        Args:
            date_from: Дата начала (YYYY-MM-DD), по умолчанию сегодня − 30 дней
            date_to: Дата окончания (YYYY-MM-DD), по умолчанию сегодня
            limit: Лимит записей

        Returns:
            Список продаж с детализацией
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        cache_key = self._cache.make_key("get_sales", date_from=date_from, date_to=date_to, limit=limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        self._wait_between_calls(2.0)

        response = self.api.get(
            "/api/v1/supplier/sales",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        result = response if isinstance(response, list) else []
        # Do not cache empty result too aggressively; it is often caused by temporary API lag.
        if result:
            self._cache.set(cache_key, result)
        return result

    def get_orders(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить отчет о заказах.

        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            limit: Лимит записей

        Returns:
            Список заказов
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        response = self.api.get(
            "/api/v1/supplier/orders",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        return response if isinstance(response, list) else []

    def get_detailed_report(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Получить детальный отчет по реализации с финансовыми показателями.

        Args:
            date_from: Дата начала (YYYY-MM-DD)
            date_to: Дата окончания (YYYY-MM-DD)
            limit: Лимит записей

        Returns:
            Детальный отчет с себестоимостью и комиссиями
        """
        if not date_from:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")

        cache_key = self._cache.make_key("get_detailed_report", date_from=date_from, date_to=date_to, limit=limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        response = self.api.get(
            "/api/v5/supplier/reportDetailByPeriod",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "limit": limit
            },
            base_url=API_ENDPOINTS["statistics"]
        )
        result = response if isinstance(response, list) else []

        self._cache.set(cache_key, result)
        return result

    def calculate_revenue(self, days: int = 30) -> Dict[str, Any]:
        """
        Рассчитать выручку за период.

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь с выручкой, количеством продаж и средним чеком
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sales = self.get_sales(date_from=date_from)

        total_revenue = sum(
            float(sale.get("forPay", 0) or 0)
            for sale in sales
            if not sale.get("isCancel", False) and not sale.get("isReturn", False)
        )
        total_sales = len(sales)
        avg_check = total_revenue / total_sales if total_sales > 0 else 0

        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),
            "total_sales": total_sales,
            "average_check": round(avg_check, 2)
        }

    def calculate_revenue_detailed(self, days: int = 30) -> Dict[str, Any]:
        """
        Рассчитать детальную выручку с учетом возвратов, комиссий и штрафов.

        Args:
            days: Количество дней для анализа

        Returns:
            Словарь с полной финансовой информацией
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        report = self.get_detailed_report(date_from=date_from)

        if not report:
            return {
                "period_days": days,
                "total_revenue": 0,
                "net_revenue": 0,
                "total_commission": 0,
                "total_returns": 0,
                "total_logistics": 0,
                "total_storage": 0,
                "penalty": 0,
                "total_sales": 0,
                "average_check": 0,
                "return_rate": 0
            }

        total_revenue = 0
        net_revenue = 0
        total_commission = 0
        total_returns = 0
        total_logistics = 0
        total_storage = 0
        penalty = 0
        sales_count = 0
        returns_count = 0

        for item in report:
            net_revenue += float(item.get("forPay", 0) or 0)

            is_return = item.get("isReturn", False)
            is_cancel = item.get("isCancel", False)

            if is_return or is_cancel:
                total_returns += float(item.get("retailAmount", 0) or 0)
                returns_count += 1
            else:
                total_revenue += float(item.get("retailAmount", 0) or 0)
                sales_count += 1

            total_commission += float(item.get("commissionAmount", 0) or 0)
            total_logistics += float(item.get("deliveryAmount", 0) or 0)
            total_storage += float(item.get("storageFee", 0) or 0)
            penalty += float(item.get("penalty", 0) or 0)

        total_operations = sales_count + returns_count

        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),
            "net_revenue": round(net_revenue, 2),
            "total_commission": round(total_commission, 2),
            "total_returns": round(total_returns, 2),
            "total_logistics": round(total_logistics, 2),
            "total_storage": round(total_storage, 2),
            "penalty": round(penalty, 2),
            "total_sales": sales_count,
            "total_returns_count": returns_count,
            "total_operations": total_operations,
            "average_check": round(total_revenue / sales_count, 2) if sales_count > 0 else 0,
            "average_net_check": round(net_revenue / sales_count, 2) if sales_count > 0 else 0,
            "return_rate": round((returns_count / total_operations * 100), 2) if total_operations > 0 else 0
        }

    def get_weekly_sales_report(self, week_start: Optional[str] = None) -> Dict[str, Any]:
        """
        Получить еженедельный отчет по продажам с детальной расшифровкой.

        Args:
            week_start: Дата начала недели (YYYY-MM-DD). Если None — берется прошлая неделя.

        Returns:
            Детальный отчет с разбивкой по дням и товарам
        """
        import pandas as pd

        if not week_start:
            today = datetime.now()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday.strftime("%Y-%m-%d")

        week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=7)
        week_end = week_end_dt.strftime("%Y-%m-%d")

        logger.info("Загрузка данных за неделю: %s - %s", week_start, week_end)

        all_sales = []
        date_from = week_start

        while True:
            batch = self.get_sales(date_from=date_from, limit=1000)
            if not batch:
                break

            all_sales.extend(batch)

            if len(batch) < 1000:
                break

            last_date = batch[-1].get('date', '')
            if not last_date or last_date[:10] > week_end:
                break

            date_from = last_date[:10] + 'T' + last_date[11:19]

        if not all_sales:
            return {
                "week_start": week_start,
                "week_end": week_end,
                "total_sales": 0,
                "total_revenue": 0,
                "error": "Нет данных за указанную неделю"
            }

        df = pd.DataFrame(all_sales)

        df['date'] = pd.to_datetime(df['date'])
        df['day'] = df['date'].dt.strftime('%Y-%m-%d')
        df['day_name'] = df['date'].dt.strftime('%A')

        df['forPay'] = pd.to_numeric(df.get('forPay', 0), errors='coerce').fillna(0)
        df['totalPrice'] = pd.to_numeric(df.get('totalPrice', 0), errors='coerce').fillna(0)
        df['finishedPrice'] = pd.to_numeric(df.get('finishedPrice', 0), errors='coerce').fillna(0)

        df['is_return'] = df.get('isCancel', False) | (df.get('saleID', '').str.contains('R', na=False))

        total_revenue = df['forPay'].sum()
        total_sales = len(df[~df['is_return']])
        total_returns = len(df[df['is_return']])

        daily_stats = df.groupby('day').agg({
            'forPay': 'sum',
            'nmId': 'count',
            'is_return': 'sum'
        }).reset_index()
        daily_stats.columns = ['date', 'revenue', 'sales_count', 'returns_count']

        product_stats = df.groupby(['nmId', 'subject', 'brand'], as_index=False).agg({
            'forPay': 'sum',
            'date': 'count',
            'is_return': 'sum'
        })
        product_stats.columns = ['nmId', 'subject', 'brand', 'revenue', 'quantity', 'returns']
        product_stats = product_stats.sort_values('revenue', ascending=False).head(20)

        category_stats = df.groupby('subject').agg({
            'forPay': 'sum',
            'nmId': 'count'
        }).reset_index()
        category_stats.columns = ['category', 'revenue', 'sales']
        category_stats = category_stats.sort_values('revenue', ascending=False).head(10)

        return {
            "week_start": week_start,
            "week_end": week_end,
            "total_revenue": round(total_revenue, 2),
            "total_sales": int(total_sales),
            "total_returns": int(total_returns),
            "return_rate": round((total_returns / (total_sales + total_returns) * 100), 2) if (total_sales + total_returns) > 0 else 0,
            "average_check": round(total_revenue / total_sales, 2) if total_sales > 0 else 0,
            "daily_breakdown": daily_stats.to_dict('records'),
            "top_products": product_stats.to_dict('records'),
            "category_breakdown": category_stats.to_dict('records'),
            "raw_data_count": len(df)
        }

    def export_weekly_report_csv(self, week_start: Optional[str] = None) -> str:
        """
        Экспортировать еженедельный отчет в CSV.

        Args:
            week_start: Дата начала недели (YYYY-MM-DD)

        Returns:
            Путь к созданному CSV файлу
        """
        import pandas as pd

        report = self.get_weekly_sales_report(week_start)

        if report.get('error'):
            return None

        daily_df = pd.DataFrame(report['daily_breakdown'])
        filename = f"weekly_report_{report['week_start']}_to_{report['week_end']}.csv"

        summary_data = {
            'Показатель': [
                'Период с',
                'Период по',
                'Общая выручка',
                'Количество продаж',
                'Количество возвратов',
                'Процент возвратов',
                'Средний чек'
            ],
            'Значение': [
                report['week_start'],
                report['week_end'],
                f"{report['total_revenue']:.2f} ₽",
                report['total_sales'],
                report['total_returns'],
                f"{report['return_rate']:.2f}%",
                f"{report['average_check']:.2f} ₽"
            ]
        }
        summary_df = pd.DataFrame(summary_data)

        with open(filename, 'w', encoding='utf-8-sig') as f:
            f.write("# СВОДКА\n")
            summary_df.to_csv(f, index=False)
            f.write("\n# ДНЕВНАЯ РАЗБИВКА\n")
            daily_df.to_csv(f, index=False)

        return filename

    def get_top_products(self, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Получить топ продаваемых товаров.

        Args:
            days: Период анализа
            limit: Количество товаров

        Returns:
            Список топовых товаров
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sales = self.get_sales(date_from=date_from)

        products = {}
        for sale in sales:
            nm_id = sale.get("nmId")
            if nm_id not in products:
                products[nm_id] = {
                    "nm_id": nm_id,
                    "name": sale.get("subject", "Unknown"),
                    "article": sale.get("supplierArticle", ""),
                    "quantity": 0,
                    "revenue": 0
                }
            products[nm_id]["quantity"] += sale.get("quantity", 0) or 1

            is_return = sale.get("isCancel", False) or sale.get("isReturn", False)
            if not is_return:
                products[nm_id]["revenue"] += float(sale.get("forPay", 0) or 0)

        sorted_products = sorted(
            products.values(),
            key=lambda x: x["revenue"],
            reverse=True
        )

        return sorted_products[:limit]

    def get_stocks_report(self) -> List[Dict]:
        """
        Получить отчет по остаткам на складах WB.

        Returns:
            Остатки по всем складам
        """
        date_from = datetime.now().strftime("%Y-%m-%d")
        response = self.api.get(
            "/api/v1/supplier/stocks",
            params={"dateFrom": date_from},
            base_url=API_ENDPOINTS["statistics"]
        )
        return response if isinstance(response, list) else []

    def get_avg_orders_by_nm_ids(
        self,
        nm_ids: List[int],
        days: int = 30,
        stock_type: str = ""
    ) -> Dict[int, float]:
        """
        Get average daily order speed for nmIDs.

        Primary source: Analytics API `/api/v2/stocks-report/products/products`
        (`docs/swagger/11-analytics.yaml`, field `metrics.avgOrders`).
        Fallback: Statistics API `/api/v1/supplier/orders` over the same period.
        """
        valid_ids = sorted({int(nm) for nm in nm_ids if int(nm) > 0})
        if not valid_ids:
            return {}

        cache_key = self._cache.make_key(
            "get_avg_orders_by_nm_ids_v3",
            nm_ids=valid_ids,
            days=days,
            stock_type=stock_type,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            normalized_cached = self._normalize_avg_orders_map(cached)
            if normalized_cached:
                return normalized_cached

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=max(days - 1, 0))
        period_days = max(days, 1)

        result: Dict[int, float] = {}
        batch_size = 1000

        # 1) Try Analytics API avgOrders first.
        # For stockType, WB docs allow "", "wb", "mp"; in practice some accounts return
        # values only for specific stock types, so we try all and keep max per nmID.
        stock_types = [stock_type] if stock_type in ("", "wb", "mp") else [""]
        if stock_type == "":
            stock_types = ["", "wb", "mp"]

        for current_stock_type in stock_types:
            for i in range(0, len(valid_ids), batch_size):
                batch_ids = valid_ids[i:i + batch_size]
                payload = {
                    "nmIDs": batch_ids,
                    "currentPeriod": {
                        "start": start_date.strftime("%Y-%m-%d"),
                        "end": end_date.strftime("%Y-%m-%d"),
                    },
                    "stockType": current_stock_type,
                    "skipDeletedNm": True,
                    "availabilityFilters": [],
                    "orderBy": {
                        "field": "avgOrders",
                        "mode": "desc",
                    },
                    "limit": 1000,
                    "offset": 0,
                }

                try:
                    response = self.api.post(
                        "/api/v2/stocks-report/products/products",
                        data=payload,
                        base_url=API_ENDPOINTS["analytics"],
                    )
                except Exception:
                    response = {}

                items = []
                if isinstance(response, dict):
                    data = response.get("data", {})
                    if isinstance(data, dict):
                        items = data.get("items", []) or []
                    elif isinstance(data, list):
                        items = data
                elif isinstance(response, list):
                    items = response

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    nm_id = item.get("nmID")
                    if nm_id is None:
                        nm_id = item.get("nmId")
                    nm_id = self._to_int_nm_id(nm_id)
                    if nm_id is None:
                        continue

                    avg_orders = 0.0
                    metrics = item.get("metrics", {})
                    if isinstance(metrics, dict):
                        avg_orders = float(metrics.get("avgOrders", 0) or 0)
                    elif "avgOrders" in item:
                        avg_orders = float(item.get("avgOrders", 0) or 0)

                    prev = float(result.get(nm_id, 0) or 0)
                    result[nm_id] = max(prev, avg_orders)

        # 2) Fallback via orders history for missing/zero nmIDs
        missing_ids = [nm for nm in valid_ids if result.get(nm, 0) <= 0]
        if missing_ids:
            qty_by_nm: Dict[int, float] = {nm: 0.0 for nm in missing_ids}
            missing_set = set(missing_ids)

            try:
                orders = self.get_orders(
                    date_from=start_date.strftime("%Y-%m-%d"),
                    date_to=end_date.strftime("%Y-%m-%d"),
                    limit=100000,
                )
                for order in orders:
                    if not isinstance(order, dict):
                        continue
                    nm_id = self._to_int_nm_id(order.get("nmId"))
                    if nm_id is None or nm_id not in missing_set:
                        continue
                    qty = order.get("quantity", 1)
                    qty_by_nm[nm_id] += float(qty or 1)
            except Exception:
                pass

            # 3) Extra fallback: sales statistics (if orders endpoint returns sparse data)
            if not any(v > 0 for v in qty_by_nm.values()):
                try:
                    sales = self.get_sales(
                        date_from=start_date.strftime("%Y-%m-%d"),
                        date_to=end_date.strftime("%Y-%m-%d"),
                        limit=100000,
                    )
                    for sale in sales:
                        if not isinstance(sale, dict):
                            continue
                        nm_id = self._to_int_nm_id(sale.get("nmId"))
                        if nm_id is None or nm_id not in missing_set:
                            continue
                        if sale.get("isCancel", False) or sale.get("isReturn", False):
                            continue
                        qty = sale.get("quantity", 1)
                        qty_by_nm[nm_id] += float(qty or 1)
                except Exception:
                    pass

            for nm_id in missing_ids:
                if qty_by_nm.get(nm_id, 0) > 0:
                    result[nm_id] = round(qty_by_nm[nm_id] / period_days, 4)

        # Avoid persisting all-zero/empty speeds: this is often a temporary API gap.
        if any(float(v or 0) > 0 for v in result.values()):
            self._cache.set(cache_key, result)
        return result

    def get_margin_by_product(self, days: int = 30) -> List[Dict]:
        """
        Рассчитать фактическую маржинальность по каждому товару
        на основе детального отчёта WB (/api/v5/supplier/reportDetailByPeriod).

        WB не передаёт себестоимость, поэтому считаем две метрики:
          - wb_cost_rate   — сколько % от выручки уходит в WB (комиссия + логистика + хранение + штрафы)
          - net_payout_rate — сколько % от выручки остаётся продавцу (forPay / retailAmount)

        Полная маржа = net_payout_rate - доля_себестоимости.
        Если ввести себестоимость, метод вернёт gross_margin_rate.

        Args:
            days: Глубина отчёта в днях (по умолчанию 30).

        Returns:
            Список словарей, отсортированных по выручке (убывание):
            {
                nm_id, vendor_code, subject, brand,
                sales_count, returns_count, return_rate,
                gross_revenue,           — выручка (сумма продаж без возвратов)
                returns_amount,          — сумма возвратов
                net_payout,             — к выплате от WB (forPay, все операции)
                avg_retail_price,        — средняя цена продажи
                avg_net_payout,          — средняя выплата за единицу
                wb_commission,           — комиссия WB
                logistics_cost,          — логистика
                storage_cost,            — хранение
                penalties,               — штрафы
                total_wb_costs,          — итого расходы WB
                wb_cost_rate,            — % выручки, уходящий в WB
                net_payout_rate,         — % выручки, остающийся продавцу
            }
        """
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cache_key = self._cache.make_key("get_margin_by_product", date_from=date_from)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        self._wait_between_calls(2.0)
        report = self.get_detailed_report(date_from=date_from, limit=100000)
        if not report:
            return []

        # Агрегируем по nmId
        agg: Dict[int, Dict] = {}

        for item in report:
            nm_id = self._to_int_nm_id(item.get("nmId"))
            if nm_id is None:
                continue

            if nm_id not in agg:
                agg[nm_id] = {
                    "nm_id":          nm_id,
                    "vendor_code":    item.get("supplierArticle", ""),
                    "subject":        item.get("subject", ""),
                    "brand":          item.get("brand", ""),
                    "sales_count":    0,
                    "returns_count":  0,
                    "gross_revenue":  0.0,
                    "returns_amount": 0.0,
                    "net_payout":     0.0,
                    "wb_commission":  0.0,
                    "logistics_cost": 0.0,
                    "storage_cost":   0.0,
                    "penalties":      0.0,
                }

            row = agg[nm_id]
            is_return = item.get("isReturn", False) or item.get("isCancel", False)

            retail_amount  = float(item.get("retailAmount",    0) or 0)
            for_pay        = float(item.get("forPay",          0) or 0)
            commission     = float(item.get("commissionAmount",0) or 0)
            delivery       = float(item.get("deliveryAmount",  0) or 0)
            storage        = float(item.get("storageFee",      0) or 0)
            penalty        = float(item.get("penalty",         0) or 0)

            row["net_payout"]     += for_pay
            row["wb_commission"]  += commission
            row["logistics_cost"] += delivery
            row["storage_cost"]   += storage
            row["penalties"]      += penalty

            if is_return:
                row["returns_count"]  += 1
                row["returns_amount"] += retail_amount
            else:
                row["sales_count"]    += 1
                row["gross_revenue"]  += retail_amount

        # Рассчитываем производные метрики
        result = []
        for row in agg.values():
            if row["sales_count"] == 0:
                continue

            gross  = row["gross_revenue"]
            payout = row["net_payout"]
            wb_costs = (row["wb_commission"] + row["logistics_cost"]
                        + row["storage_cost"] + row["penalties"])

            total_ops = row["sales_count"] + row["returns_count"]

            result.append({
                **row,
                "total_wb_costs":  round(wb_costs, 2),
                "avg_retail_price": round(gross / row["sales_count"], 2),
                "avg_net_payout":   round(payout / row["sales_count"], 2),
                "return_rate":      round(row["returns_count"] / total_ops * 100, 1) if total_ops else 0.0,
                "wb_cost_rate":     round(wb_costs / gross * 100, 1) if gross else 0.0,
                "net_payout_rate":  round(payout / gross * 100, 1) if gross else 0.0,
                # округляем денежные поля
                "gross_revenue":    round(gross, 2),
                "returns_amount":   round(row["returns_amount"], 2),
                "net_payout":       round(payout, 2),
                "wb_commission":    round(row["wb_commission"], 2),
                "logistics_cost":   round(row["logistics_cost"], 2),
                "storage_cost":     round(row["storage_cost"], 2),
                "penalties":        round(row["penalties"], 2),
            })

        result.sort(key=lambda x: x["gross_revenue"], reverse=True)

        if result:
            self._cache.set(cache_key, result)
        return result

