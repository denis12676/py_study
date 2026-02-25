"""Тест получения остатков FBS с chrtIds"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wb_client import WildberriesAPI, WBConfig, API_ENDPOINTS
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
print()

config = WBConfig(api_token=token)
api = WildberriesAPI(config)

warehouse_id = 1588930  # ИП_Ангар_Белая_Дача

# Шаг 1: Получаем товары чтобы извлечь chrtIds
print("="*60)
print("ШАГ 1: Получение товаров для извлечения chrtIds")
print("="*60)

chrt_ids = []
try:
    # Пробуем получить товары через content API
    response = api.post(
        "/content/v2/get/cards/list",
        data={
            "settings": {
                "cursor": {"limit": 100},
                "filter": {"withPhoto": -1}
            }
        },
        base_url=API_ENDPOINTS["content"]
    )
    
    if isinstance(response, dict) and 'cards' in response:
        cards = response['cards']
        print(f"✓ Получено карточек: {len(cards)}")
        
        for card in cards[:5]:  # Берем первые 5 для теста
            nm_id = card.get('nmID')
            sizes = card.get('sizes', [])
            for size in sizes:
                chrt_id = size.get('chrtID')
                if chrt_id:
                    chrt_ids.append(chrt_id)
                    print(f"  ✓ Товар {nm_id}: chrtId {chrt_id}")
                    break  # Берем только первый размер
            
            if len(chrt_ids) >= 5:
                break
    else:
        print(f"✗ Неожиданный ответ: {type(response)}")
        
except Exception as e:
    print(f"✗ Ошибка получения товаров: {e}")

print()

# Шаг 2: Запрашиваем остатки с chrtIds
print("="*60)
print("ШАГ 2: Запрос остатков с chrtIds")
print("="*60)

if chrt_ids:
    print(f"✓ Отправляем {len(chrt_ids)} chrtIds: {chrt_ids}")
    
    try:
        response = api.post(
            f"/api/v3/stocks/{warehouse_id}",
            data={
                "chrtIds": chrt_ids,
                "skus": []
            },
            base_url=API_ENDPOINTS["marketplace"]
        )
        
        print(f"✓ Тип ответа: {type(response)}")
        
        if isinstance(response, dict):
            stocks = response.get('stocks', [])
            print(f"✓ Товаров в ответе: {len(stocks)}")
            
            if stocks:
                for stock in stocks[:3]:
                    print(f"  📦 {stock}")
            else:
                print("  ✗ Пустой список stocks")
                print(f"  Ответ: {response}")
        else:
            print(f"✗ Неожиданный тип: {response}")
            
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
else:
    print("✗ Нет chrtIds для теста")

print()

# Шаг 3: Пробуем с null вместо пустого массива
print("="*60)
print("ШАГ 3: Пробуем с null/skips")
print("="*60)

try:
    response = api.post(
        f"/api/v3/stocks/{warehouse_id}",
        data={
            "chrtIds": None,  # Пробуем null
            "skus": []
        },
        base_url=API_ENDPOINTS["marketplace"]
    )
    
    print(f"✓ С null chrtIds: {type(response)}")
    if isinstance(response, dict):
        print(f"  Товаров: {len(response.get('stocks', []))}")
        
except Exception as e:
    print(f"✗ С null: {e}")

# Шаг 4: Пробуем вообще без тела
print()
print("="*60)
print("ШАГ 4: Пробуем без тела запроса (GET)")
print("="*60)

try:
    response = api.get(
        f"/api/v3/stocks/{warehouse_id}",
        base_url=API_ENDPOINTS["marketplace"]
    )
    
    print(f"✓ GET запрос: {type(response)}")
    print(f"  Ответ: {response}")
    
except Exception as e:
    print(f"✗ GET ошибка: {e}")

print()
print("="*60)
print("РЕКОМЕНДАЦИИ:")
print("="*60)
print("""
Если товары есть, но API возвращает 0:

1. Проверьте доступ токена к категории Marketplace (склады продавца)
   - В ЛК WB: Настройки → API Интеграции → Проверьте доступы

2. Возможно нужен другой API endpoint
   - Попробуйте /api/v2/stocks (статистика)
   - Или /api/v3/stocks (без warehouseId)

3. Проверьте что товары реально на этом складе:
   - В ЛК WB: Склады → Остатки
   - Найдите склад "ИП_Ангар_Белая_Дача"
   - Проверьте что там есть товары с остатками > 0

4. Если товары есть в ЛК, но API возвращает 0:
   - Обратитесь в поддержку WB API
   - Возможно ограничение для вашего типа аккаунта
""")
