# Исправление расчета выручки в Wildberries AI Agent

## Проблема
Была обнаружена ошибка в расчете выручки - использовалось поле `totalPrice` вместо `forPay`, что приводило к завышенным показателям.

## Решение

### Изменен метод: `calculate_revenue()`

**Было:**
```python
total_revenue = sum(float(sale.get("totalPrice", 0)) for sale in sales)
```

**Стало:**
```python
total_revenue = sum(float(sale.get("forPay", 0) or 0) for sale in sales)
```

## Объяснение полей API

### Поле `totalPrice`
- Цена товара **БЕЗ** учета скидок
- Завышенное значение
- **НЕ** использовать для расчета реальной выручки

### Поле `forPay`  
- Сумма к выплате продавцу
- Учитывает все скидки (SPP, скидка продавца)
- Учитывает комиссию WB
- **ПРАВИЛЬНОЕ** значение для выручки

### Поле `finishedPrice`
- Цена со всеми скидками
- Цена, которую платит покупатель
- Можно использовать как альтернативу

## Результат

После исправления:
- Выручка отображается корректно
- Учитываются все вычеты WB
- Нет завышенных показателей

## Дополнительно

Добавлено кэширование для:
- `get_sales()` - кэш 5 минут
- `get_detailed_report()` - кэш 5 минут

Это снижает нагрузку на API и предотвращает ошибку 429 (Too Many Requests).

## Пример использования

```python
from ai_agent import WildberriesAIAgent

agent = WildberriesAIAgent("ваш_токен")

# Простая выручка (использует forPay)
revenue = agent.analytics.calculate_revenue(days=30)
print(f"Выручка: {revenue['total_revenue']} ₽")

# Детальная выручка (с разбивкой по вычетам)
detailed = agent.analytics.calculate_revenue_detailed(days=30)
print(f"Валовая: {detailed['total_revenue']} ₽")
print(f"Чистая: {detailed['net_revenue']} ₽")
print(f"Комиссия WB: {detailed['total_commission']} ₽")
```

## Проверка

После обновления:
1. Перезапустите дашборд: `streamlit run dashboard.py`
2. Перейдите в раздел "Аналитика"
3. Выберите период и нажмите "Обновить"
4. Выручка должна отображаться корректно

## Технические детали

API Endpoints:
- Statistics API: `https://statistics-api.wildberries.ru`
- Метод Sales: `GET /api/v1/supplier/sales`
- Rate Limit: 1 запрос/минуту

Rate Limiter:
- Автоматические паузы между запросами
- Кэширование на 5 минут
- Retry при ошибках
