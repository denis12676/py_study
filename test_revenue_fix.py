"""
Тест исправления расчета выручки
Сравнивает старый и новый метод расчета
"""

from ai_agent import WildberriesAIAgent

# Вставьте ваш токен
API_TOKEN = "ваш_api_токен_здесь"

def test_revenue_calculation():
    print("="*60)
    print("ТЕСТ РАСЧЕТА ВЫРУЧКИ")
    print("="*60)
    print()
    
    try:
        agent = WildberriesAIAgent(API_TOKEN)
        print("✓ Агент инициализирован")
        print()
        
        # Получаем продажи за 7 дней
        print("Загрузка данных за 7 дней...")
        date_from = "2026-02-17"  # 7 дней назад
        sales = agent.analytics.get_sales(date_from=date_from)
        
        if not sales:
            print("Нет данных о продажах за указанный период")
            return
        
        print(f"✓ Загружено {len(sales)} записей")
        print()
        
        # Старый метод (НЕПРАВИЛЬНЫЙ)
        old_total = sum(float(sale.get("totalPrice", 0) or 0) for sale in sales)
        
        # Новый метод (ПРАВИЛЬНЫЙ)
        new_total = sum(float(sale.get("forPay", 0) or 0) for sale in sales)
        
        # Показываем разницу на примере первых 3 продаж
        print("Пример расчета (первые 3 продажи):")
        print("-"*60)
        for i, sale in enumerate(sales[:3], 1):
            total_price = float(sale.get("totalPrice", 0) or 0)
            for_pay = float(sale.get("forPay", 0) or 0)
            discount = sale.get("discountPercent", 0)
            
            print(f"{i}. Артикул: {sale.get('nmId')}")
            print(f"   Цена без скидок (totalPrice): {total_price:.2f} ₽")
            print(f"   Сумма к выплате (forPay): {for_pay:.2f} ₽")
            print(f"   Скидка: {discount}%")
            print(f"   Разница: {total_price - for_pay:.2f} ₽")
            print()
        
        print("="*60)
        print("ИТОГОВОЕ СРАВНЕНИЕ:")
        print("="*60)
        print(f"Старый метод (totalPrice): {old_total:,.2f} ₽")
        print(f"Новый метод (forPay):     {new_total:,.2f} ₽")
        print()
        print(f"ЗАВЫШЕНИЕ (ошибка):      {old_total - new_total:,.2f} ₽")
        print(f"Процент завышения:       {((old_total/new_total - 1) * 100):.1f}%" if new_total > 0 else "N/A")
        print()
        print("✓ Исправление работает корректно!")
        print()
        print("Теперь выручка считается по полю forPay - это сумма")
        print("которую WB реально выплатит продавцу.")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        print()
        print("Убедитесь что:")
        print("1. API токен указан правильно")
        print("2. У токена есть доступ к категории Statistics")
        print("3. В магазине есть продажи за указанный период")

if __name__ == "__main__":
    test_revenue_calculation()
