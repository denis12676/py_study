"""Тест API v2 для остатков FBS"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

token = os.environ.get("WB_API_TOKEN")
if not token:
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('WB_API_TOKEN='):
                    token = line.strip().split('=', 1)[1].strip('"\'')
                    break
    except:
        pass

if not token:
    print("❌ Токен не найден")
    sys.exit(1)

print(f"✓ Токен: {token[:20]}...")
print()

config = WBConfig(api_token=token)
api = WildberriesAPI(config)

# Тест 1: Пробуем API v2/stocks
print("="*60)
print("ТЕСТ 1: POST /api/v2/stocks (статистика)")
print("="*60)

try:
    today = datetime.now().strftime("%Y-%m-%d")
    
    response = api.post(
        "/api/v2/stocks",
        data={
            "dateFrom": today,
            "dateTo": today,
            "warehouseIds": []  # Пустой список = все склады
        },
        base_url=API_ENDPOINTS["statistics"]
    )
    
    print(f"✓ Тип ответа: {type(response)}")
    if isinstance(response, list):
        print(f"✓ Записей: {len(response)}")
        if response:
            print(f"✓ Пример: {response[0]}")
    elif isinstance(response, dict):
        print(f"✓ Ответ: {response}")
    else:
        print(f"✓ Ответ: {response}")
        
except Exception as e:
    print(f"✗ Ошибка: {e}")

print()

# Тест 2: Пробуем marketplace API без warehouseId
print("="*60)
print("ТЕСТ 2: POST /api/v3/stocks (без warehouseId)")
print("="*60)

try:
    response = api.post(
        "/api/v3/stocks",
        data={"chrtIds": [], "skus": []},
        base_url=API_ENDPOINTS["marketplace"]
    )
    
    print(f"✓ Тип ответа: {type(response)}")
    if isinstance(response, dict):
        stocks = response.get('stocks', [])
        print(f"✓ Товаров: {len(stocks)}")
        if stocks:
            print(f"✓ Пример: {stocks[0]}")
    elif isinstance(response, list):
        print(f"✓ Товаров: {len(response)}")
        if response:
            print(f"✓ Пример: {response[0]}")
    else:
        print(f"✓ Ответ: {response}")
        
except Exception as e:
    print(f"✗ Ошибка: {e}")
    print(f"  Вероятно, требуется warehouseId")

print()
print("="*60)
print("Вывод:")
print("="*60)
print("""
Если все тесты возвращают 0 товаров или ошибки:

1. У вас нет товаров на FBS складах (все на FBO)
2. Для ценообразования используйте только FBO остатки:
   - Данные уже есть на вкладке FBO
   - Суммарные остатки по регионам и складам WB

3. Если должны быть товары на FBS:
   - Проверьте в ЛК WB: Настройки → Склады
   - Убедитесь что товары привязаны к складам FBS
""")
