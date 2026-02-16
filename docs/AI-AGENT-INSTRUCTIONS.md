# Инструкция для ИИ-агента: модели и схемы

При любых изменениях, связанных с передачей данных между сервисами или с API сайта, придерживайся следующих правил.

---

## 1. Связь между сервисами: только модели, не DTO

Для обмена данными между сервисами (database_service ↔ web_service, database_service ↔ bot_service, при необходимости web_service ↔ bot_service) используй **модели** — форму данных, соответствующую доменным сущностям.

**Что использовать:** структуру полей из `infrastructure/shared/models/` (User, Space, ServiceTicket, Feedback, Object, PollAnswer, ServiceTicketLog, SpaceView, UserAuth и т.д.). Сериализация в JSON при отправке по HTTP — по полям этих сущностей (через Converter или через Pydantic-модель с теми же полями, что и у сущности). На приёмной стороне десериализуй JSON в ту же структуру (dict или Pydantic-модель с полями сущности). Типы и поля бери из объявлений в `shared/models/*.py` (ORM-модели задают контракт полей).

**Папку `infrastructure/shared/models/dto/` необходимо полностью удалить.** Не используй классы из неё; все обращения к ним замени на модели сущностей (межсервис) или на схемы из `web_service/api/schemas/` (API сайта). После переноса всех использований — удали папку `shared/models/dto/` и все импорты из неё в проекте.

**Итог:** между сервисами передаются данные в формате **моделей** (сущности из shared/models). Папка dto в shared не используется и подлежит удалению.

---

## 2. API сайта: только схемы в web_service

Для HTTP-API, которое вызывает фронт (эндпоинты web_service под /api/v1), используй только схемы из `infrastructure/services/web_service/src/api/schemas/`.

**Что использовать:** в `api/schemas/` лежат request- и response-модели для каждого эндпоинта: Create*Request, Update*Body, MessageResponse, ServiceTicketsStatsResponse и т.д. Для ответов «одна сущность» или «список сущностей» можно импортировать из shared модель сущности (если в shared заведены Pydantic-модели с полями сущности для сериализации) или описать response-схему в schemas с теми же полями, что ожидает фронт. Контракт полей сверяй с `web/lib/api.ts` и `web/types/index.ts`.

Папки `shared/models/dto/` в проекте нет (она удалена). Всё, что относится к формату запроса/ответа эндпоинтов сайта, должно находиться только в `web_service/src/api/schemas/`.

**Итог:** для работы сайта используются только **схемы** в `web_service/api/schemas/`.

---

## 3. Краткая сводка

| Назначение | Где брать форму данных |
|------------|------------------------|
| Связь между сервисами (HTTP database ↔ web, database ↔ bot, web ↔ bot) | Модели сущностей из `shared/models/` (поля из ORM-моделей или Pydantic-модели с той же структурой) |
| API сайта (запросы и ответы эндпоинтов web_service) | `web_service/src/api/schemas/` |

Папка `shared/models/dto/` в проекте удалена и не используется.

---

## 4. Удаление папки dto и рефакторинг

Папку `infrastructure/shared/models/dto/` нужно **полностью удалить**.

**Перед удалением:** найди все импорты из `shared.models.dto`, `shared.models.dto.*` или `from shared.models.dto import ...` в проекте (infrastructure: database_service, web_service, bot_service, shared). Замени их: для межсервисного обмена — на использование моделей сущностей из `shared/models/` (и при необходимости Pydantic-моделей с той же структурой для сериализации); для эндпоинтов сайта — на схемы из `web_service/src/api/schemas/`. Обнови `shared/models/__init__.py`, если из него экспортируются DTO. После этого удали целиком папку `infrastructure/shared/models/dto/` (все файлы в ней и саму папку).

**Если при работе встречаешь код, который ещё импортирует dto:** замени импорт на модель сущности или на схему из web_service/api/schemas, затем убедись, что папка dto удалена.
