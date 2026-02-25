# Wildberries API Swagger Specifications

Эта папка содержит OpenAPI (Swagger) спецификации для API Wildberries.

## Полный список файлов (14 штук)

| № | Файл | Размер | Описание |
|---|------|---------|----------|
| 01 | `01-general.yaml` | 48K | Общая информация, авторизация, новости, информация о продавце |
| 02 | `02-products.yaml` | 319K | Управление товарами: категории, характеристики, создание карточек |
| 03 | `03-orders-fbs.yaml` | 153K | Заказы FBS (Fulfillment By Seller) |
| 04 | `04-orders-dbw.yaml` | 77K | Заказы DBW (Delivery By Wildberries) |
| 05 | `05-orders-dbs.yaml` | 128K | Заказы DBS (Delivery By Seller) |
| 06 | `06-in-store-pickup.yaml` | 94K | Заказы с самовывоза |
| 07 | `07-orders-fbw.yaml` | 49K | Поставки FBW (Fulfillment By Wildberries) |
| 08 | `08-promotion.yaml` | 215K | Маркетинг и продвижение: кампании, ставки |
| 09 | `09-communications.yaml` | 170K | Общение с покупателями: вопросы, отзывы, чат |
| 10 | `10-tariffs.yaml` | 41K | Тарифы: комиссии, стоимость услуг |
| 11 | `11-analytics.yaml` | 232K | Аналитика: воронка продаж, поисковые запросы, остатки |
| 12 | `12-reports.yaml` | 153K | Отчёты: поставки, склады, заказы, продажи |
| 13 | `13-finances.yaml` | 45K | Документы и бухгалтерия: финансовые отчёты |
| 14 | `14-wbd.yaml` | 128K | Wildberries Цифровой: офферы, контент |

## Источник

Файлы скачаны с официального портала Wildberries API:
- URL шаблон: `https://dev.wildberries.ru/api/swagger/yaml/ru/{номер}-{раздел}.yaml`
- Swagger UI: https://dev.wildberries.ru/swagger/general
- Документация: https://dev.wildberries.ru/

## Разделы Swagger UI

Все 14 разделов доступны в выпадающем меню Swagger на сайте:
1. Общее (general)
2. Работа с товарами (products)
3. Заказы FBS (orders-fbs)
4. Заказы DBW (orders-dbw)
5. Заказы DBS (orders-dbs)
6. Заказы Самовывоз (in-store-pickup)
7. Поставки FBW (orders-fbw)
8. Маркетинг и продвижение (promotion)
9. Общение с покупателями (communications)
10. Тарифы (tariffs)
11. Аналитика и данные (analytics)
12. Отчёты (reports)
13. Документы и бухгалтерия (finances)
14. Wildberries Цифровой (wbd)

## Использование

Эти спецификации можно использовать для:
- Генерации клиентов API (OpenAPI Generator)
- Импорта в Postman
- Создания документации
- Автоматического тестирования

## Примечания

- Все 14 файлов успешно скачаны и проверены
- Все файлы содержат валидные OpenAPI 3.0.1 спецификации
- Общий размер: ~1.9 MB
- Дата скачивания: 25.02.2026
