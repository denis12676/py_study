"""
price_history.py — журнал изменений цен с поддержкой отката.

Хранит каждое изменение цены в SQLite.
Позволяет откатить цену одного товара или все изменения за период.

Схема таблицы
-------------
price_history(
    id            INTEGER  PRIMARY KEY AUTOINCREMENT,
    nm_id         INTEGER  NOT NULL,
    vendor_code   TEXT,
    title         TEXT,
    old_price     REAL     NOT NULL,
    old_discount  INTEGER  NOT NULL,
    new_price     REAL     NOT NULL,
    new_discount  INTEGER  NOT NULL,
    strategy_name TEXT,
    reason        TEXT,
    applied       INTEGER  DEFAULT 0,   -- 1 если отправлено в API
    rolled_back   INTEGER  DEFAULT 0,   -- 1 если откат выполнен
    created_at    TEXT     NOT NULL     -- ISO 8601
)

Использование
-------------
    from price_history import PriceHistoryDB
    from pricing_strategy import PricingEngine, StockStrategy

    db = PriceHistoryDB()

    # Записать результаты прогона движка
    engine = PricingEngine(...)
    actions = engine.run(dry_run=False)
    db.record_many(actions)

    # Посмотреть историю конкретного товара
    rows = db.get_by_nm_id(nm_id=123456, limit=10)

    # Откатить последнее изменение одного товара
    db.rollback_last(nm_id=123456, products_mgr=agent.products)

    # Откатить все изменения за последние 24 часа
    db.rollback_since(hours=24, products_mgr=agent.products)
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from pricing_strategy import PriceAction

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent / "price_history.db"


class PriceHistoryDB:
    """
    SQLite-журнал изменений цен.

    Thread-safe (WAL mode + check_same_thread=False).

    Args:
        db_path: Путь к файлу БД. По умолчанию price_history.db рядом с модулем.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = str(db_path or _DEFAULT_DB)
        self._init_db()

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    nm_id         INTEGER NOT NULL,
                    vendor_code   TEXT    DEFAULT '',
                    title         TEXT    DEFAULT '',
                    old_price     REAL    NOT NULL,
                    old_discount  INTEGER NOT NULL,
                    new_price     REAL    NOT NULL,
                    new_discount  INTEGER NOT NULL,
                    strategy_name TEXT    DEFAULT '',
                    reason        TEXT    DEFAULT '',
                    applied       INTEGER DEFAULT 0,
                    rolled_back   INTEGER DEFAULT 0,
                    created_at    TEXT    NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ph_nm_id     ON price_history(nm_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ph_created   ON price_history(created_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ph_applied   ON price_history(applied)"
            )

    # ------------------------------------------------------------------
    # Запись
    # ------------------------------------------------------------------

    def record(self, action: PriceAction) -> int:
        """
        Записать одно изменение цены.

        Returns:
            id новой записи.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO price_history
                    (nm_id, vendor_code, title,
                     old_price, old_discount, new_price, new_discount,
                     strategy_name, reason, applied, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.nm_id,
                    action.vendor_code,
                    action.title,
                    action.old_price,
                    action.old_discount,
                    action.new_price,
                    action.new_discount,
                    action.strategy_name,
                    action.reason,
                    1 if action.applied else 0,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            row_id = cur.lastrowid
        logger.debug(
            "price_history: записан id=%d nmID=%d %s → %d руб (скидка %d%%)",
            row_id, action.nm_id, action.vendor_code,
            action.new_price, action.new_discount,
        )
        return row_id

    def record_many(self, actions: List[PriceAction]) -> int:
        """
        Записать список изменений за один прогон движка.

        Returns:
            Количество записанных строк.
        """
        if not actions:
            return 0
        count = 0
        for action in actions:
            self.record(action)
            count += 1
        logger.info("price_history: записано %d изменений", count)
        return count

    # ------------------------------------------------------------------
    # Чтение
    # ------------------------------------------------------------------

    def get_by_nm_id(self, nm_id: int, limit: int = 20) -> List[dict]:
        """
        История изменений одного товара (от новых к старым).

        Args:
            nm_id: Артикул WB.
            limit: Максимальное количество записей.

        Returns:
            Список словарей с полями записи.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM price_history
                WHERE nm_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (nm_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        applied_only: bool = False,
        limit: int = 200,
    ) -> List[dict]:
        """
        Все изменения за период.

        Args:
            date_from:    ISO дата начала, например "2026-02-01".
            date_to:      ISO дата конца.
            applied_only: Только реально применённые (applied=1).
            limit:        Максимальное количество записей.

        Returns:
            Список словарей, от новых к старым.
        """
        clauses = []
        params: list = []

        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to + "T23:59:59")
        if applied_only:
            clauses.append("applied = 1")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM price_history {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def get_last_applied(self, nm_id: int) -> Optional[dict]:
        """
        Последнее реально применённое изменение для товара.
        Используется для отката.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM price_history
                WHERE nm_id = ? AND applied = 1 AND rolled_back = 0
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (nm_id,),
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Откат
    # ------------------------------------------------------------------

    def rollback_last(self, nm_id: int, products_mgr) -> bool:
        """
        Откатить последнее применённое изменение цены одного товара.

        Args:
            nm_id:        Артикул WB.
            products_mgr: ProductsManager для вызова update_price.

        Returns:
            True если откат выполнен, False если нечего откатывать.
        """
        record = self.get_last_applied(nm_id)
        if not record:
            logger.warning(
                "rollback_last: нет применённых изменений для nmID=%d", nm_id
            )
            return False

        try:
            products_mgr.update_price(
                nm_id=nm_id,
                price=record["old_price"],
                discount=record["old_discount"],
            )
            self._mark_rolled_back(record["id"])
            logger.info(
                "rollback_last: nmID=%d %s восстановлена цена %d руб (скидка %d%%)",
                nm_id, record.get("vendor_code", ""),
                record["old_price"], record["old_discount"],
            )
            return True
        except Exception as exc:
            logger.error(
                "rollback_last: ошибка отката nmID=%d: %s", nm_id, exc, exc_info=True
            )
            return False

    def rollback_since(self, hours: int = 24, products_mgr = None) -> Dict[int, bool]:
        """
        Откатить все применённые изменения за последние N часов.

        Args:
            hours:        Глубина отката в часах.
            products_mgr: ProductsManager.

        Returns:
            Словарь {nm_id: True/False} — результат по каждому товару.
        """
        since = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM price_history
                WHERE applied = 1 AND rolled_back = 0 AND created_at >= ?
                ORDER BY created_at DESC
                """,
                (since,),
            ).fetchall()

        if not rows:
            logger.info("rollback_since: нет изменений за последние %d ч", hours)
            return {}

        # Берём только последнее изменение для каждого nm_id
        seen: dict = {}
        for row in rows:
            nm_id = row["nm_id"]
            if nm_id not in seen:
                seen[nm_id] = dict(row)

        logger.info(
            "rollback_since: откат %d товаров за последние %d ч", len(seen), hours
        )

        results: Dict[int, bool] = {}
        for nm_id, record in seen.items():
            try:
                products_mgr.update_price(
                    nm_id=nm_id,
                    price=record["old_price"],
                    discount=record["old_discount"],
                )
                self._mark_rolled_back(record["id"])
                results[nm_id] = True
                logger.info(
                    "rollback_since: nmID=%d восстановлена цена %d руб",
                    nm_id, record["old_price"],
                )
            except Exception as exc:
                results[nm_id] = False
                logger.error(
                    "rollback_since: ошибка nmID=%d: %s", nm_id, exc
                )

        success = sum(1 for v in results.values() if v)
        logger.info("rollback_since: успешно %d / %d", success, len(results))
        return results

    def _mark_rolled_back(self, record_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE price_history SET rolled_back = 1 WHERE id = ?",
                (record_id,),
            )

    # ------------------------------------------------------------------
    # Статистика
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """
        Сводная статистика по журналу.

        Returns:
            Словарь с ключами: total, applied, rolled_back, unique_products,
            date_first, date_last, by_strategy.
        """
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM price_history"
            ).fetchone()[0]

            applied = conn.execute(
                "SELECT COUNT(*) FROM price_history WHERE applied = 1"
            ).fetchone()[0]

            rolled_back = conn.execute(
                "SELECT COUNT(*) FROM price_history WHERE rolled_back = 1"
            ).fetchone()[0]

            unique_products = conn.execute(
                "SELECT COUNT(DISTINCT nm_id) FROM price_history"
            ).fetchone()[0]

            date_first = conn.execute(
                "SELECT MIN(created_at) FROM price_history"
            ).fetchone()[0]

            date_last = conn.execute(
                "SELECT MAX(created_at) FROM price_history"
            ).fetchone()[0]

            by_strategy_rows = conn.execute(
                """
                SELECT strategy_name, COUNT(*) as cnt
                FROM price_history
                GROUP BY strategy_name
                ORDER BY cnt DESC
                """
            ).fetchall()

        return {
            "total": total,
            "applied": applied,
            "rolled_back": rolled_back,
            "unique_products": unique_products,
            "date_first": date_first,
            "date_last": date_last,
            "by_strategy": {r["strategy_name"]: r["cnt"] for r in by_strategy_rows},
        }

    def purge_old(self, days: int = 90) -> int:
        """
        Удалить записи старше N дней.

        Returns:
            Количество удалённых строк.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM price_history WHERE created_at < ?", (cutoff,)
            )
            deleted = cur.rowcount
        logger.info("purge_old: удалено %d записей старше %d дней", deleted, days)
        return deleted
