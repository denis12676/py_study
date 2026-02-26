"""
scheduler.py — планировщик автоматической переоценки товаров.

Использует APScheduler 3.x для фонового или автономного запуска.

Режимы запуска
--------------
1. Фоновый — внутри Streamlit или другого приложения:

    from scheduler import PriceScheduler
    from pricing_strategy import PricingEngine, StockStrategy

    engine = PricingEngine(agent.products, agent.analytics, agent.inventory,
                           strategies=[StockStrategy()])
    scheduler = PriceScheduler(engine, dry_run=False)
    scheduler.add_interval(hours=4)
    scheduler.start()                  # не блокирует поток
    ...
    scheduler.stop()

2. Автономный процесс (блокирует поток до Ctrl+C):

    python scheduler.py

3. Разовый запуск (без планировщика):

    python scheduler.py --once
"""

import argparse
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

from logging_config import setup_logging
from pricing_strategy import PriceAction, PricingEngine

logger = logging.getLogger(__name__)

JOB_ID = "auto_reprice"


# ---------------------------------------------------------------------------
# Результат одного запуска
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """Итог одного цикла переоценки."""
    started_at: datetime
    finished_at: datetime
    dry_run: bool
    actions_count: int           # сколько товаров рекомендовано изменить
    applied_count: int           # сколько реально отправлено в API
    error: Optional[str] = None
    actions: List[PriceAction] = field(default_factory=list)

    @property
    def duration_sec(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def __str__(self) -> str:
        status = "DRY-RUN" if self.dry_run else "APPLIED"
        if self.error:
            return (
                f"[{status}] {self.started_at:%Y-%m-%d %H:%M:%S} "
                f"— ОШИБКА: {self.error} "
                f"({self.duration_sec:.1f}с)"
            )
        return (
            f"[{status}] {self.started_at:%Y-%m-%d %H:%M:%S} "
            f"— {self.actions_count} изменений"
            + (f", применено {self.applied_count}" if not self.dry_run else "")
            + f" ({self.duration_sec:.1f}с)"
        )


# ---------------------------------------------------------------------------
# Основной планировщик
# ---------------------------------------------------------------------------

class PriceScheduler:
    """
    Планировщик автоматической переоценки товаров.

    Args:
        engine:      Настроенный PricingEngine со стратегиями.
        dry_run:     True — только расчёт без отправки в API.
        max_history: Сколько последних RunResult хранить в памяти.
    """

    def __init__(
        self,
        engine: PricingEngine,
        dry_run: bool = True,
        max_history: int = 50,
    ):
        self.engine = engine
        self.dry_run = dry_run
        self.max_history = max_history

        self._scheduler = BackgroundScheduler(
            job_defaults={"misfire_grace_time": 60 * 10},  # 10 мин опоздания
            timezone="Europe/Moscow",
        )
        self._history: List[RunResult] = []
        self._running = False

    # ------------------------------------------------------------------
    # Настройка расписания
    # ------------------------------------------------------------------

    def add_interval(self, hours: int = 4, minutes: int = 0) -> "PriceScheduler":
        """
        Запускать переоценку каждые N часов [и M минут].

        Пример:
            scheduler.add_interval(hours=4)       # каждые 4 часа
            scheduler.add_interval(hours=0, minutes=30)  # каждые 30 минут
        """
        self._remove_existing_job()
        self._scheduler.add_job(
            self._run_job,
            trigger=IntervalTrigger(hours=hours, minutes=minutes),
            id=JOB_ID,
            name=f"auto_reprice every {hours}h{minutes}m",
            replace_existing=True,
        )
        logger.info("Расписание: каждые %dч %dм", hours, minutes)
        return self

    def add_cron(self, hour: int = 2, minute: int = 0) -> "PriceScheduler":
        """
        Запускать переоценку каждый день в заданное время.

        Пример:
            scheduler.add_cron(hour=2, minute=0)   # каждый день в 02:00
            scheduler.add_cron(hour=8, minute=30)  # каждый день в 08:30
        """
        self._remove_existing_job()
        self._scheduler.add_job(
            self._run_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=JOB_ID,
            name=f"auto_reprice daily at {hour:02d}:{minute:02d}",
            replace_existing=True,
        )
        logger.info("Расписание: каждый день в %02d:%02d", hour, minute)
        return self

    def _remove_existing_job(self) -> None:
        if self._scheduler.get_job(JOB_ID):
            self._scheduler.remove_job(JOB_ID)

    # ------------------------------------------------------------------
    # Управление
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Запустить планировщик в фоне (не блокирует поток)."""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return
        self._scheduler.start()
        self._running = True
        job = self._scheduler.get_job(JOB_ID)
        if job and job.next_run_time:
            logger.info("Планировщик запущен. Следующий запуск: %s",
                        job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"))

    def stop(self) -> None:
        """Остановить планировщик."""
        if not self._running:
            return
        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Планировщик остановлен")

    def run_now(self) -> RunResult:
        """Запустить переоценку немедленно (вне расписания)."""
        logger.info("Ручной запуск переоценки (dry_run=%s)", self.dry_run)
        return self._run_job()

    # ------------------------------------------------------------------
    # Состояние
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Текущее состояние планировщика."""
        job = self._scheduler.get_job(JOB_ID) if self._running else None
        last = self._history[-1] if self._history else None
        return {
            "running": self._running,
            "dry_run": self.dry_run,
            "job_name": job.name if job else None,
            "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if (job and job.next_run_time) else None,
            "last_run": str(last) if last else "Ещё не запускался",
            "total_runs": len(self._history),
            "strategies": [s.name for s in self.engine.strategies],
        }

    def get_history(self, n: int = 10) -> List[RunResult]:
        """Вернуть последние N результатов запусков."""
        return self._history[-n:]

    # ------------------------------------------------------------------
    # Внутренний цикл
    # ------------------------------------------------------------------

    def _run_job(self) -> RunResult:
        """Один цикл переоценки: сбор данных → оценка → применение."""
        started_at = datetime.now()
        logger.info("--- Старт переоценки (dry_run=%s) ---", self.dry_run)

        try:
            actions = self.engine.run(dry_run=self.dry_run)
            applied = sum(1 for a in actions if a.applied)

            result = RunResult(
                started_at=started_at,
                finished_at=datetime.now(),
                dry_run=self.dry_run,
                actions_count=len(actions),
                applied_count=applied,
                actions=actions,
            )
            logger.info("--- Переоценка завершена: %s ---", result)

            if actions:
                summary = self.engine.summary(actions)
                logger.info("\n%s", summary)

        except Exception as exc:
            result = RunResult(
                started_at=started_at,
                finished_at=datetime.now(),
                dry_run=self.dry_run,
                actions_count=0,
                applied_count=0,
                error=str(exc),
            )
            logger.error("Ошибка переоценки: %s", exc, exc_info=True)

        self._history.append(result)
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

        return result


# ---------------------------------------------------------------------------
# Автономный запуск: python scheduler.py
# ---------------------------------------------------------------------------

def _build_engine_from_env() -> PricingEngine:
    """Создать PricingEngine из переменных окружения."""
    load_dotenv()
    token = os.environ.get("WB_API_TOKEN")
    if not token:
        logger.error("Переменная WB_API_TOKEN не задана. Добавьте её в .env файл.")
        sys.exit(1)

    from ai_agent import WildberriesAIAgent
    from pricing_strategy import (
        ConversionStrategy,
        SeasonPeriod,
        SeasonStrategy,
        StockStrategy,
    )

    agent = WildberriesAIAgent(api_token=token)

    strategies = [
        StockStrategy(
            low_threshold=int(os.getenv("STOCK_LOW_THRESHOLD", "10")),
            low_markup=float(os.getenv("STOCK_LOW_MARKUP", "0.10")),
            high_threshold=int(os.getenv("STOCK_HIGH_THRESHOLD", "150")),
            high_discount=int(os.getenv("STOCK_HIGH_DISCOUNT", "5")),
        ),
        ConversionStrategy(
            no_sales_days=int(os.getenv("CONV_NO_SALES_DAYS", "7")),
            discount_delta=int(os.getenv("CONV_DISCOUNT_DELTA", "5")),
            max_discount=int(os.getenv("CONV_MAX_DISCOUNT", "50")),
        ),
        SeasonStrategy(periods=[
            SeasonPeriod("Чёрная пятница", "11-20", "12-05", discount_add=10),
            SeasonPeriod("Новогодняя распродажа", "12-20", "01-05", discount_add=15),
        ]),
    ]

    return PricingEngine(
        products_mgr=agent.products,
        analytics_mgr=agent.analytics,
        inventory_mgr=agent.inventory,
        strategies=strategies,
    )


def main():
    setup_logging()

    parser = argparse.ArgumentParser(description="Планировщик переоценки Wildberries")
    parser.add_argument("--once",     action="store_true",  help="Разовый запуск без планировщика")
    parser.add_argument("--apply",    action="store_true",  help="Применить изменения (по умолчанию dry-run)")
    parser.add_argument("--interval", type=int, default=4,  help="Интервал в часах (по умолчанию 4)")
    parser.add_argument("--cron",     type=str, default=None, help="Время запуска HH:MM (например 02:00)")
    args = parser.parse_args()

    dry_run = not args.apply
    engine  = _build_engine_from_env()

    if args.once:
        # Разовый запуск — просто запустить и выйти
        scheduler = PriceScheduler(engine, dry_run=dry_run)
        result = scheduler.run_now()
        print(result)
        sys.exit(0 if not result.error else 1)

    # Постоянный планировщик (блокирующий режим)
    blocking_scheduler = BlockingScheduler(
        job_defaults={"misfire_grace_time": 600},
        timezone="Europe/Moscow",
    )

    def _job():
        inner = PriceScheduler(engine, dry_run=dry_run)
        result = inner.run_now()
        logger.info("Следующий запуск по расписанию.")
        return result

    if args.cron:
        try:
            h, m = map(int, args.cron.split(":"))
        except ValueError:
            logger.error("Неверный формат --cron. Используйте HH:MM, например 02:00")
            sys.exit(1)
        blocking_scheduler.add_job(_job, CronTrigger(hour=h, minute=m), id=JOB_ID)
        logger.info("Режим: ежедневно в %02d:%02d (dry_run=%s)", h, m, dry_run)
    else:
        blocking_scheduler.add_job(_job, IntervalTrigger(hours=args.interval), id=JOB_ID)
        logger.info("Режим: каждые %d ч (dry_run=%s)", args.interval, dry_run)

    def _shutdown(signum, frame):
        logger.info("Получен сигнал %s, остановка...", signum)
        blocking_scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Планировщик запущен. Нажмите Ctrl+C для остановки.")
    blocking_scheduler.start()


if __name__ == "__main__":
    main()
