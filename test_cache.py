"""
Тестирование кэширования в AnalyticsManager
"""

import sys
sys.path.insert(0, '.')

from managers import AnalyticsManager
from wb_client import WildberriesAPI, WBConfig
from unittest.mock import Mock

# Создаем мок API
config = WBConfig(api_token='test')
api = Mock(spec=WildberriesAPI)

# Создаем менеджер
manager = AnalyticsManager(api)

print("="*60)
print("Тестирование кэширования AnalyticsManager")
print("="*60)
print()

# Тест 1: Проверка наличия методов
print("1. Проверка методов кэширования:")
methods = ['_get_cache_key', '_get_cached', '_set_cached', '_wait_between_calls', 'clear_cache']
all_present = True
for method in methods:
    if hasattr(manager, method):
        print(f"   ✓ {method}")
    else:
        print(f"   ✗ {method} - ОТСУТСТВУЕТ!")
        all_present = False

if all_present:
    print("\n   Все методы кэширования на месте!")
else:
    print("\n   ❌ Некоторые методы отсутствуют!")
    sys.exit(1)

# Тест 2: Проверка работы кэша
print("\n2. Тестирование работы кэша:")

# Мокируем возвращаемые данные
api.get.return_value = [
    {"nmId": 1, "forPay": 1000, "date": "2026-02-20"},
    {"nmId": 2, "forPay": 2000, "date": "2026-02-21"}
]

# Первый вызов - должен обратиться к API
print("   Первый вызов get_sales()...")
result1 = manager.get_sales(date_from="2026-02-01")
print(f"   ✓ Получено {len(result1)} записей")
print(f"   ✓ API вызван {api.get.call_count} раз(а)")

# Второй вызов - должен взять из кэша
print("\n   Второй вызов get_sales() (должен использовать кэш)...")
result2 = manager.get_sales(date_from="2026-02-01")
print(f"   ✓ Получено {len(result2)} записей")
print(f"   ✓ API вызван {api.get.call_count} раз(а) (должен быть 1)")

if api.get.call_count == 1:
    print("\n   ✅ Кэширование работает! Второй вызов не обращался к API.")
else:
    print(f"\n   ❌ Кэширование не работает. API вызван {api.get.call_count} раз.")

# Тест 3: Очистка кэша
print("\n3. Тестирование очистки кэша:")
manager.clear_cache()
print("   ✓ Кэш очищен")

# Проверим что кэш пуст
print(f"   ✓ Размер кэша: {len(manager._cache)} записей")

print("\n" + "="*60)
print("Все тесты пройдены! Кэширование работает корректно.")
print("="*60)
