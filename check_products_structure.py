"""Проверка структуры товаров и их chrtIds"""
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

# Получаем товары
print("="*60)
print("ПОЛУЧЕНИЕ ТОВАРОВ")
print("="*60)

try:
    response = api.post(
        "/content/v2/get/cards/list",
        data={
            "settings": {
                "cursor": {"limit": 10},
                "filter": {"withPhoto": -1}
            }
        },
        base_url=API_ENDPOINTS["content"]
    )
    
    if isinstance(response, dict) and 'cards' in response:
        cards = response['cards']
        print(f"✓ Получено карточек: {len(cards)}")
        print()
        
        for i, card in enumerate(cards[:3]):  # Первые 3 товара
            nm_id = card.get('nmID')
            title = card.get('title', '')[:40]
            sizes = card.get('sizes', [])
            
            print(f"Товар {i+1}: {title}")
            print(f"  nmID: {nm_id}")
            print(f"  Количество размеров: {len(sizes)}")
            
            if sizes:
                for size in sizes:
                    chrt_id = size.get('chrtID')
                    skus = size.get('skus', [])
                    tech_size = size.get('techSize', '')
                    print(f"    - chrtID: {chrt_id}, techSize: {tech_size}, skus: {skus}")
            else:
                print("    ⚠️ Нет размеров (sizes пустой)")
                # Проверим есть ли другие поля
                print(f"    Поля товара: {list(card.keys())}")
            
            print()
    else:
        print(f"✗ Неожиданный ответ: {response}")
        
except Exception as e:
    print(f"✗ Ошибка: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("АЛЬТЕРНАТИВНЫЕ МЕТОДЫ ПОЛУЧЕНИЯ ОСТАТКОВ")
print("="*60)
print()

warehouse_id = 1588930

# Пробуем с nmIds вместо chrtIds
print("ТЕСТ 1: Пробуем с nmIds (если API поддерживает)")
try:
    response = api.post(
        f"/api/v3/stocks/{warehouse_id}",
        data={
            "nmIds": [cards[0].get('nmID')] if 'cards' in dir() and cards else [],
            "skus": []
        },
        base_url=API_ENDPOINTS["marketplace"]
    )
    print(f"  Ответ: {response}")
except Exception as e:
    print(f"  Ошибка: {e}")

# Пробуем вообще без body
print()
print("ТЕСТ 2: POST без тела")
try:
    response = api.post(
        f"/api/v3/stocks/{warehouse_id}",
        data=None,
        base_url=API_ENDPOINTS["marketplace"]
    )
    print(f"  Ответ: {response}")
except Exception as e:
    print(f"  Ошибка: {e}")

print()
print("="*60)
print("ВЫВОД:")
print("="*60)
print("""
Если у товаров нет размеров (sizes=[]), то chrtId не существует.

Возможные решения:
1. API /api/v3/stocks/{warehouseId} требует chrtIds - без них не работает
2. Для товаров без размеров нужен другой метод API
3. Возможно стоит использовать API v2 или статистику

Проверьте в ЛК WB раздел "Склады → Остатки" - 
какие данные там доступны для ваших товаров?
""")
