"""
AnalyticsManager — продвинутая аналитика и расчет прибыли.
"""

import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from wb_client import WildberriesAPI, API_ENDPOINTS
from cache import APICache
from models import Sale, Order

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self, api: WildberriesAPI):
        self.api = api
        self._cache = APICache(ttl=600)
        self.db_path = Path(__file__).parent.parent / "wb_cache.db"

    async def get_detailed_report_async(self, date_from: Optional[str] = None, date_to: Optional[str] = None, limit: int = 100000) -> List[Dict]:
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        response = await self.api.aget("/api/v5/supplier/reportDetailByPeriod", params={"dateFrom": date_from, "dateTo": date_to, "limit": limit}, base_url=API_ENDPOINTS["statistics"])
        return response if isinstance(response, list) else []

    async def sync_reports_to_db(self, user_id: int, days: int = 90) -> Dict[str, Any]:
        """Загрузка детальных отчетов WB в локальную БД с привязкой к пользователю"""
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        report_data = await self.get_detailed_report_async(date_from=date_from)
        
        saved = 0
        if report_data:
            with sqlite3.connect(self.db_path) as conn:
                for item in report_data:
                    try:
                        oper_name = item.get("supplier_oper_name", "").lower()
                        is_return = "возврат" in oper_name or "отмена" in oper_name
                        
                        conn.execute("""
                            INSERT OR REPLACE INTO financial_reports 
                            (user_id, report_date, nm_id, vendor_code, subject_name, brand_name,
                             supplier_oper_name, retail_amount, for_pay, commission,
                             delivery, storage, penalty, quantity, is_return)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            user_id, item.get("rr_dt", datetime.now().strftime("%Y-%m-%d")),
                            item.get("nm_id"), item.get("sa_name", ""),
                            item.get("subject_name", ""), item.get("brand_name", ""),
                            item.get("supplier_oper_name", ""),
                            float(item.get("retail_amount", 0) or 0),
                            float(item.get("ppvz_for_pay", 0) or 0),
                            float(item.get("ppvz_sales_commission", 0) or 0),
                            float(item.get("delivery_rub", 0) or 0),
                            float(item.get("storage_fee", 0) or 0),
                            float(item.get("penalty", 0) or 0),
                            int(item.get("quantity", 0) or 0), is_return
                        ))
                        saved += 1
                    except: continue
                conn.commit()
        return {"loaded": len(report_data), "saved": saved}

    def get_full_pnl_data(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Сбор полных данных P&L (Profit and Loss) из БД.
        Объединяет данные WB и ручной ввод пользователя.
        """
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 1. Агрегация данных WB
            wb_stats = conn.execute("""
                SELECT 
                    SUM(retail_amount) as gross_revenue,
                    SUM(for_pay) as net_payout,
                    SUM(commission) as total_commission,
                    SUM(delivery) as total_logistics,
                    SUM(storage) as total_storage,
                    SUM(penalty) as total_penalties,
                    COUNT(*) as total_operations
                FROM financial_reports 
                WHERE user_id = ? AND report_date >= ?
            """, (user_id, date_limit)).fetchone()
            
            # 2. Расчет COGS (Себестоимость проданных товаров)
            # Берем количество продаж каждого товара и умножаем на purchase_price из product_costs
            cogs_data = conn.execute("""
                SELECT SUM(fr.quantity * pc.purchase_price) as total_cogs,
                       SUM(fr.retail_amount * (pc.tax_percent / 100)) as total_taxes
                FROM financial_reports fr
                JOIN product_costs pc ON fr.nm_id = pc.nm_id AND fr.user_id = pc.user_id
                WHERE fr.user_id = ? AND fr.report_date >= ? AND fr.is_return = 0
            """, (user_id, date_limit)).fetchone()

            # 3. Прочие расходы
            expenses = conn.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND date >= ?", 
                                  (user_id, date_limit)).fetchone()[0] or 0.0

        res = dict(wb_stats) if wb_stats['gross_revenue'] else {
            "gross_revenue": 0, "net_payout": 0, "total_commission": 0, 
            "total_logistics": 0, "total_storage": 0, "total_penalties": 0, "total_operations": 0
        }
        
        res["total_cogs"] = cogs_data["total_cogs"] or 0.0
        res["total_taxes"] = cogs_data["total_taxes"] or 0.0
        res["other_expenses"] = expenses
        
        # Финальный расчет чистой прибыли
        # net_payout уже включает (Выручка - Комиссия), но WB может вычитать логистику отдельно
        # Формула: net_payout - logistics - storage - penalties - cogs - taxes - other_expenses
        res["net_profit"] = (
            res["net_payout"] - 
            res["total_logistics"] - 
            res["total_storage"] - 
            res["total_penalties"] - 
            res["total_cogs"] - 
            res["total_taxes"] - 
            res["other_expenses"]
        )
        
        return res

    def get_margin_by_product(self, user_id: int, days: int = 30) -> List[Dict]:
        """
        Расчет маржинальности по каждому товару с учетом себестоимости.
        """
        date_limit = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Агрегируем данные из отчетов и джойним себестоимость
            query = """
                SELECT 
                    fr.nm_id, 
                    fr.vendor_code, 
                    fr.subject_name as name,
                    SUM(fr.retail_amount) as revenue,
                    SUM(fr.for_pay) as payout,
                    SUM(fr.delivery) as logistics,
                    SUM(fr.quantity) as quantity,
                    pc.purchase_price,
                    pc.tax_percent
                FROM financial_reports fr
                LEFT JOIN product_costs pc ON fr.nm_id = pc.nm_id AND fr.user_id = pc.user_id
                WHERE fr.user_id = ? AND fr.report_date >= ? AND fr.is_return = 0
                GROUP BY fr.nm_id
            """
            rows = conn.execute(query, (user_id, date_limit)).fetchall()
            
        result = []
        for row in rows:
            r = dict(row)
            purchase_price = r['purchase_price'] or 0.0
            tax_rate = r['tax_percent'] or 6.0
            
            # Расчет прибыли на единицу товара
            total_cogs = r['quantity'] * purchase_price
            total_taxes = r['revenue'] * (tax_rate / 100)
            
            # Чистая прибыль по товару = Выплата_от_WB - Логистика - Себестоимость - Налоги
            net_profit = r['payout'] - r['logistics'] - total_cogs - total_taxes
            
            result.append({
                "nm_id": r['nm_id'],
                "vendor_code": r['vendor_code'],
                "name": r['name'],
                "quantity": r['quantity'],
                "revenue": round(r['revenue'], 2),
                "net_profit": round(net_profit, 2),
                "margin": round((net_profit / r['revenue'] * 100), 1) if r['revenue'] > 0 else 0
            })
            
        return sorted(result, key=lambda x: x['net_profit'], reverse=True)

    # --- Sync Wrappers & Fallbacks ---
    async def get_sales_async(self, **kwargs):
        resp = await self.api.aget("/api/v1/supplier/sales", params=kwargs, base_url=API_ENDPOINTS["statistics"])
        return [Sale.model_validate(s) for s in resp] if isinstance(resp, list) else []

    def calculate_revenue(self, days=30):
        return asyncio.run(self.calculate_revenue_async(days))

    async def calculate_revenue_async(self, days=30):
        date_f = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sales = await self.get_sales_async(dateFrom=date_f)
        total = sum(s.for_pay for s in sales if s.is_real_sale)
        return {"total_revenue": total, "total_sales": len(sales)}

    def get_db_stats(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                res = conn.execute("SELECT COUNT(*), MIN(report_date), MAX(report_date) FROM financial_reports").fetchone()
                return {"total_records": res[0], "date_from": res[1], "date_to": res[2], "unique_products": 0}
        except: return {"total_records": 0}
