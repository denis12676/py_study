"""Отладка API остатков FBS"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS
from managers import ProductsManager
from dotenv import load_dotenv

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
print(f"✓ Marketplace API: {API_ENDPOINTS['marketplace']}")
print()

config = WBConfig(api_token=token)
api = WildberriesAPI(config)
manager = ProductsManager(api)

# Шаг 1: Получаем склады
print("="*60)
print("ШАГ 1: Получение списка складов")
print("="*60)

try:
    warehouses = manager.get_warehouses()
    print(f"✓ Найдено складов: {len(warehouses)}")
    
    if warehouses:
        for wh in warehouses:
            wh_id = wh.get('id')
            wh_name = wh.get('name', 'Unknown')
            print(f"  - ID: {wh_id}, Название: {wh_name}")
            
            # Шаг 2: Пробуем получить остатки для этого склада
            print(f"\n  📦 Загрузка остатков для склада {wh_id}...")
            
            try:
                response = api.post(
                    f"/api/v3/stocks/{wh_id}",
                    data={"chrtIds": [], "skus": []},
                    base_url=API_ENDPOINTS["marketplace"]
                )
                
                print(f"  ✓ Тип ответа: {type(response)}")
                
                if isinstance(response, dict):
                    stocks = response.get('stocks', [])
                    print(f"  ✓ Количество товаров: {len(stocks)}")
                    
                    if stocks:
                        print(f"  ✓ Первый товар: {stocks[0]}")
                elif isinstance(response, list):
                    print(f"  ✓ Количество товаров: {len(response)}")
                    if response:
                        print(f"  ✓ Первый товар: {response[0]}")
                else:
                    print(f"  ✗ Неожиданный формат: {response}")
                    
            except Exception as e:
                print(f"  ✗ Ошибка: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("✗ Склады не найдены!")
        
except Exception as e:
    print(f"✗ Ошибка получения складов: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("ШАГ 3: Проверка метода get_stocks()")
print("="*60)

try:
    # Пробуем получить остатки через метод менеджера
    if warehouses:
        wh_id = warehouses[0].get('id')
        stocks = manager.get_stocks(wh_id)
        print(f"✓ Метод get_stocks() вернул: {len(stocks)} записей")
        if stocks:
            print(f"✓ Пример записи: {stocks[0]}")
        else:
            print("✗ Пустой список")
except Exception as e:
    print(f"✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("ОТЛАДКА ЗАВЕРШЕНА")
print("="*60)
