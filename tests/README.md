# 🧪 Тесты для Wildberries AI Agent

Эта директория содержит автоматические тесты для предотвращения регрессий.

## 📁 Структура тестов

```
tests/
├── conftest.py          # Фикстуры и конфигурация pytest
├── test_wb_client.py    # Тесты API клиента
├── test_managers.py     # Тесты бизнес-логики
├── test_ai_agent.py     # Тесты AI агента
└── test_dashboard.py    # Тесты Streamlit UI
```

## 🚀 Быстрый старт

### Установка зависимостей

```bash
# Установить dev-зависимости
pip install -r requirements-dev.txt

# Или только pytest
pip install pytest pytest-cov pytest-mock responses
```

### Запуск всех тестов

```bash
# Запустить все тесты
pytest

# Запустить с подробным выводом
pytest -v

# Запустить с покрытием кода
pytest --cov=. --cov-report=html

# Запустить только unit-тесты (быстро)
pytest -m unit

# Исключить медленные тесты
pytest -m "not slow"
```

### Запуск конкретных тестов

```bash
# Тесты API клиента
pytest tests/test_wb_client.py

# Тесты менеджеров
pytest tests/test_managers.py -v

# Тесты AI агента
pytest tests/test_ai_agent.py::TestRequestAnalysis -v

# Конкретный тест
pytest tests/test_managers.py::TestAnalyticsManager::test_calculate_revenue_uses_forpay -v
```

## 📊 Типы тестов

### Unit тесты (быстрые)
- Изолированные, не требуют API
- Проверяют логику и расчеты
- Используют моки

```bash
pytest -m unit
```

### Integration тесты (медленные)
- Требуют реальный API токен
- Проверяют работу с WB API
- Могут упасть при проблемах с сетью

```bash
# Требуется токен в переменной окружения
export WB_API_TOKEN=your_token_here
pytest -m integration
```

### UI тесты
- Тестируют Streamlit компоненты
- Требуют mock библиотеки

```bash
pytest tests/test_dashboard.py
```

## 🎯 Ключевые тесты

### Тесты расчета выручки

```bash
# Проверка что используется forPay (а не totalPrice)
pytest tests/test_managers.py::TestAnalyticsManager::test_calculate_revenue_uses_forpay -v

# Проверка детального отчета
pytest tests/test_managers.py::TestAnalyticsManager::test_calculate_revenue_detailed -v
```

### Тесты распознавания запросов

```bash
# Проверка всех типов запросов
pytest tests/test_ai_agent.py::TestRequestAnalysis -v

# Проверка извлечения параметров
pytest tests/test_ai_agent.py::TestParameterExtraction -v
```

### Тесты API клиента

```bash
# Проверка обработки ошибок
pytest tests/test_wb_client.py::TestWildberriesAPI::test_http_error_handling -v

# Проверка rate limiting
pytest tests/test_wb_client.py::TestWildberriesAPI::test_429_rate_limit_retry -v
```

## 🛠️ Добавление новых тестов

### Шаблон теста

```python
import pytest
from unittest.mock import Mock

def test_feature_name():
    """Описание что тестируется"""
    # Arrange
    mock_api = Mock()
    manager = MyManager(mock_api)
    
    # Act
    result = manager.do_something()
    
    # Assert
    assert result == expected_value
    mock_api.get.assert_called_once()
```

### Использование фикстур

```python
def test_with_fixture(mock_api, sample_product):
    """Использование фикстур из conftest.py"""
    manager = ProductsManager(mock_api)
    mock_api.post.return_value = sample_product
    
    result = manager.get_all_products()
    
    assert result["nmID"] == 123456
```

### Параметризованные тесты

```python
import pytest

@pytest.mark.parametrize("query,expected_action", [
    ("покажи товары", "list_products"),
    ("выручка", "revenue_report"),
    ("топ товаров", "top_products"),
])
def test_query_recognition(agent, query, expected_action):
    result = agent._analyze_request(query)
    assert result["action"] == expected_action
```

## 📈 Покрытие кода

```bash
# Генерация отчета о покрытии
pytest --cov=. --cov-report=html

# Открыть отчет
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

## 🔍 Отладка тестов

```bash
# Запуск с отладчиком
pytest --pdb

# Остановка на первой ошибке
pytest -x

# Показать локальные переменные при ошибке
pytest -l

# Подробный traceback
pytest --tb=long
```

## 📝 Пример вывода тестов

```
$ pytest -v

============================= test session starts ==============================
platform win32 -- Python 3.11.0, pytest-7.4.0, pluggy-1.2.0
rootdir: C:\wbagent\wildberries-ai-agent
configfile: pytest.ini
tests/test_wb_client.py::TestWBConfig::test_default_values PASSED         [  5%]
tests/test_wb_client.py::TestRateLimiter::test_rate_limit_values PASSED  [ 10%]
tests/test_managers.py::TestAnalyticsManager::test_calculate_revenue_uses_forpay PASSED [ 15%]
...

============================= 42 passed in 2.34s ==============================
```

## 🚨 CI/CD интеграция

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-dev.txt
      - run: pytest -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### Pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest -x -q
        language: system
        types: [python]
        pass_filenames: false
        always_run: true
```

## 💡 Лучшие практики

1. **Всегда тестируйте граничные случаи**
   - Пустые списки
   - Нулевые значения
   - Очень большие числа

2. **Используйте моки для внешних API**
   - Не делайте реальные запросы в unit-тестах
   - Проверяйте правильность вызовов

3. **Тестируйте ошибки**
   - 404 Not Found
   - 429 Too Many Requests
   - Timeout

4. **Давайте тестам понятные имена**
   - `test_calculate_revenue_with_discounts`
   - `test_api_client_handles_429_retry`

5. **Группируйте тесты в классы**
   - Логическое разделение по функционалу
   - Использование shared fixtures

## 📚 Полезные ссылки

- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Python testing best practices](https://realpython.com/pytest-python-testing/)

---

**Запускайте тесты перед каждым коммитом!** 🚀
