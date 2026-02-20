# Аудит: dict vs модели в общении между сервисами

## Архитектура

1. **database_service** всегда возвращает `Converter.to_dict(result)` → JSON/dict по HTTP
2. **db_client._call** при переданном `_model_class` преобразует `result["data"]` из dict в модель
3. **bot_client**, **media_client** не передают entity-объекты, только простые payload

---

## ✅ Уже используют model_class (работа с моделями)

### bot_service
- `user_service`: create, get_by_id, get_all, update — `model_class=User`
- `service_ticket_service`: create, get_by_id, get_by_msid, get_all, update — `model_class=ServiceTicket`
- `rental_object_service`: create, get_by_id, get_all, update — `model_class=Object`
- `rental_space_service`: create, get_by_id, get_by_object_id, get_all, update — `model_class=Space`
- `feedback_service`: create, get_by_id, get_all, update — `model_class=Feedback`
- `poll_service`: create, get_by_id, get_all, update, find — `model_class=PollAnswer`
- `notification_service`: audit_log.find_by_entity — `model_class=AuditLog`
- `guest_parking_callback`: guest_parking.create — `model_class=GuestParkingRequest`

### web_service
- `auth`: get_by_username, get_by_id — `model_class=User`
- `users`: create, get_by_id — `model_class=User`
- `service_tickets`: create, get_by_id, update — `model_class=ServiceTicket`

---

## ❌ НЕ передают model_class (всё ещё dict)

### web_service — db_client вызовы без model_class

| Роутер         | Метод              | Вызов                          | Нужна модель   |
|----------------|--------------------|---------------------------------|----------------|
| guest_parking  | get_by_id          | get_by_id(entity_id)            | GuestParkingRequest |
| guest_parking  | get_by_id          | data.get("user_id") — dict!    | ✓              |
| feedbacks      | create             | create(model_data=...)         | Feedback       |
| feedbacks      | get_by_id          | get_by_id(entity_id)           | Feedback       |
| audit_log      | find_by_entity     | find_by_entity(...)             | AuditLog       |
| space_views    | create             | create(model_data=...)         | SpaceView      |
| space_views    | get_all            | get_all()                      | SpaceView      |
| space_views    | get_by_id          | get_by_id(entity_id)           | SpaceView      |
| polls          | create             | create(model_data=...)         | PollAnswer     |
| polls          | get_all            | get_all()                      | PollAnswer     |
| polls          | get_by_id          | get_by_id(entity_id)           | PollAnswer     |
| rental_spaces  | create             | create(model_data=...)         | Space          |
| rental_spaces  | find               | find(filters=...)              | Space          |
| rental_spaces  | get_by_id          | get_by_id(entity_id)           | Space          |
| rental_objects | create             | create(model_data=...)         | Object         |
| rental_objects | get_by_id          | get_by_id(entity_id)           | Object         |
| service_tickets| find (by msid)     | find(filters={"msid": ...})    | ServiceTicket  |
| service_tickets| get_stats          | get_stats()                    | — (возвращает stats, не entity) |

---

## ⚠️ Баг в database_client.py

```python
# get_paginated НЕ передаёт _model_class в _call!
async def get_paginated(self, ..., model_class: Any = None):
    return await self._call(
        "get_paginated",
        page=...,
        # _model_class=model_class  ← ОТСУТСТВУЕТ!
    )
```

Даже если передать `model_class`, он игнорируется.

---

## ⚠️ Ограничение _call для get_paginated

Текущая логика `_call`:
- `data` — список → конвертирует каждый элемент
- `data` — dict → конвертирует весь dict как одну сущность

Для `get_paginated` приходит `data = {items: [...], total: N}`. Сейчас это обрабатывалось бы как одна сущность, что некорректно. Нужна обработка формата `{items, total}`.

---

## enrichment.py — специальный случай

`batch_fetch_objects` и `batch_fetch_users` используют dict:
- `obj.get("id")`, `obj.get("name")`
- `result[uid] = u` — сохраняют dict для lookup
- Enrichers мутируют `items` in place: `u["object"] = ...`

Для enrichment pipeline предметы должны быть dict — т.к. enricher добавляет поля `user`, `object` и т.д. Модели SQLAlchemy не имеют этих атрибутов. Поэтому:
- `get_paginated` возвращает items как dict
- Перед enricher items остаются dict
- После enrichment — dict для response

**Вывод**: batch_fetch и enrichers остаются dict-based — это внутренняя реализация. Между сервисами через db_client можно возвращать модели, но для списков с enrichment проще оставить dict до enrichment.

---

## Рекомендации

1. **Исправить get_paginated** в database_client: передавать `_model_class` и добавить в `_call` разбор формата `{items, total}`.
2. **Добавить model_class** во все вызовы web_service, возвращающие одиночные entity: guest_parking, feedbacks, audit_log, space_views, polls, rental_spaces, rental_objects.
3. **service_tickets find(msid)** — добавить `model_class=ServiceTicket`, затем перед возвратом конвертировать в dict и enrich.
4. **enrichment** — оставить работу с dict; это не «между серверами», а внутренняя обработка данных.
