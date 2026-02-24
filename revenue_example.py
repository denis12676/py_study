# Пример использования calculate_revenue_detailed

from ai_agent import WildberriesAIAgent

agent = WildberriesAIAgent("ваш_токен")

# Простая выручка (валовая)
simple = agent.analytics.calculate_revenue(days=30)
print(f"Валовая выручка: {simple['total_revenue']} ₽")
print(f"Продаж: {simple['total_sales']}")
print(f"Средний чек: {simple['average_check']} ₽")

# Детальная выручка (с учетом вычетов)
detailed = agent.analytics.calculate_revenue_detailed(days=30)
print(f"\n=== ДЕТАЛЬНЫЙ ОТЧЕТ ===")
print(f"Валовая выручка: {detailed['total_revenue']:,.2f} ₽")
print(f"Возвраты: {detailed['total_returns']:,.2f} ₽")
print(f"Чистая к выплате: {detailed['net_revenue']:,.2f} ₽")
print(f"Комиссия WB: {detailed['total_commission']:,.2f} ₽")
print(f"Логистика: {detailed['total_logistics']:,.2f} ₽")
print(f"Хранение: {detailed['total_storage']:,.2f} ₽")
print(f"Штрафы: {detailed['penalty']:,.2f} ₽")
print(f"\nКоличество продаж: {detailed['total_sales']}")
print(f"Количество возвратов: {detailed['total_returns_count']}")
print(f"Процент возвратов: {detailed['return_rate']:.2f}%")
print(f"\nСредний чек (валовой): {detailed['average_check']:,.2f} ₽")
print(f"Средний чек (чистый): {detailed['average_net_check']:,.2f} ₽")
