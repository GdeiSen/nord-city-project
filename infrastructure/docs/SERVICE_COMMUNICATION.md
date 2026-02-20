# Межсервисное взаимодействие в Nord City

## Архитектура

```
┌─────────────────┐     HTTP RPC      ┌─────────────────────┐     HTTP RPC      ┌──────────────────┐
│   web_service   │ ◄───────────────► │  database_service   │                   │  media_service   │
│   (FastAPI)     │                   │  (FastAPI)          │ ◄───────────────► │  (FastAPI)       │
│   :8000         │                   │  :8001              │                   │  :8004           │
└────────┬────────┘                   └─────────────────────┘                   └──────────────────┘
         │                                       ▲
         │ HTTP RPC                              │ HTTP RPC
         ▼                                       │
┌─────────────────┐                              │
│   bot_service   │ ◄────────────────────────────┘
│   (Telegram)    │   (bot вызывает db_client)
│   :8002         │
└─────────────────┘
```

Все взаимодействие идёт через **HTTP RPC** на единый endpoint `/internal/rpc` каждого сервиса.

---

## 1. HttpRpcClient — низкоуровневый транспорт

**Файл:** `shared/clients/http_rpc_client.py`

```python
# Тело запроса (JSON)
payload = {
    "service": "user",      # имя сервиса
    "method": "get_by_id",  # метод
    "params": {"entity_id": 1}  # параметры (должны быть JSON-сериализуемы)
}

# Ответ (JSON)
{
    "success": True,
    "data": {...},    # или None при ошибке
    "error": None    # или строка при ошибке
}
```

- Транспорт не знает о доменных типах
- Передаёт только `dict`, получает `dict`
- Использует `httpx` для POST-запросов

---

## 2. DatabaseClient — типизированный прокси к database_service

**Файл:** `shared/clients/database_client.py`

### Прокси-объекты

```python
db_client.user           # CRUD + get_by_username, get_by_ids
db_client.service_ticket # CRUD + get_stats, get_by_msid
db_client.object         # CRUD + get_by_ids
db_client.space          # CRUD + get_by_object_id
db_client.feedback       # CRUD
db_client.poll           # CRUD
db_client.guest_parking  # CRUD
db_client.audit_log      # CRUD + find_by_entity
db_client.space_view     # CRUD
db_client.otp            # verify_code, invalidate_user_codes, create
db_client.auth           # CRUD (auth records)
```

### Передача данных с моделями (схемами)

#### Входящие параметры (вызов RPC)

1. **Примитивы** (`entity_id`, `page`, `page_size`, …) — передаются как есть
2. **Сложные объекты** — сериализуются через `Converter.to_dict()`:
   - Pydantic-схема → `model_dump()`
   - SQLAlchemy ORM → колонки в dict

```python
# Вызов create — два варианта:
await db_client.user.create(
    model_instance=UserSchema(id=1, username="...", ...),  # Pydantic
    model_class=UserSchema   # для десериализации ответа
)

# или
await db_client.user.create(
    model_data={"id": 1, "username": "...", ...},  # dict напрямую
    model_class=UserSchema
)
```

Внутри `_call()`:

```python
serializable = {k: Converter.to_dict(v) for k, v in params.items()}
result = await self._client.call(self._service, method, serializable)
```

#### Ответ (десериализация)

Если передан `model_class` (Pydantic-схема):

```python
# Одиночный объект
result["data"] = Converter.from_dict(UserSchema, data)

# Список
result["data"] = [Converter.from_dict(UserSchema, item) for item in data]

# Пагинация {items, total}
result["data"] = {
    "items": [Converter.from_dict(UserSchema, item) for item in data["items"]],
    "total": data["total"]
}
```

`Converter.from_dict(PydanticClass, dict)` → вызывает `model_class.model_validate(data)`.

---

## 3. database_service — приём и обработка RPC

**Файл:** `database_service/src/main.py`

### Обработчик RPC

```python
# 1. Парсинг запроса
service_name = request["service"]   # "user"
method_name = request["method"]     # "get_by_id"
params = request["params"]          # {"entity_id": 1}

# 2. Преобразование model_data → model_instance (только для create)
if "model_data" in params:
    model_class = service_instance.model_class  # ORM (User, ServiceTicket, ...)
    params["model_instance"] = Converter.from_dict(model_class, params["model_data"])
    del params["model_data"]

# 3. Вызов метода сервиса
result = await method_to_call(**params)  # ORM-экземпляр или список

# 4. Сериализация ответа
return {"success": True, "data": Converter.to_dict(result)}
```

### Важно

- **database_service** использует **ORM** (SQLAlchemy) для работы с БД
- `model_class` у сервисов — это **ORM** (User, Object, ServiceTicket, …)
- `Converter.from_dict(ORM, dict)` создаёт ORM-экземпляр для записи в БД
- `Converter.to_dict(orm_instance)` сериализует ORM в dict для JSON

---

## 4. Цепочка данных (пример: create User)

```
[web_service / bot_service]

UserSchema(id=1, username="...")  или  dict
         │
         ▼
db_client.user.create(model_instance=schema, model_class=UserSchema)
         │
         │  Converter.to_dict(schema) → dict
         │
         ▼
HttpRpcClient.call("user", "create", {model_data: {...}})
         │
         │  POST /internal/rpc  Body: {service, method, params}
         │
         ▼
[database_service]
         │
         │  params["model_data"] → Converter.from_dict(User, dict) → ORM User
         │  UserService.create(model_instance=User_ORM)
         │  → repository.create() → INSERT в PostgreSQL
         │
         │  result = created_orm_instance
         │  Converter.to_dict(orm) → dict
         │
         ▼
{"success": true, "data": {"id": 1, "username": "...", ...}}

         ▼
[db_client]  Converter.from_dict(UserSchema, data) → UserSchema
         │
         ▼
Caller получает UserSchema (Pydantic)
```

---

## 5. BotClient — вызовы bot_service

**Файл:** `shared/clients/bot_client.py`

```python
bot_client.notification.notify_new_ticket(ticket_id=123)
bot_client.notification.edit_ticket_message(ticket_id=123)
bot_client.notification.delete_ticket_messages(ticket_id=123)
bot_client.notification.notify_ticket_completion(ticket_id=123)
bot_client.telegram_auth.send_otp_code(user_id=456)
```

- **Не передаёт** доменные объекты (тикеты, юзеры)
- Передаёт только ID и примитивы
- bot_service сам получает данные через `db_client` при необходимости

---

## 6. MediaClient — вызовы media_service

**Файл:** `shared/clients/media_client.py`

- Загрузка файла: base64 в params
- Ответ: `{path, url}`

Доменные модели не участвуют.

---

## 7. Converter — единая сериализация

**Файл:** `shared/utils/converter.py`

| Вход | to_dict | from_dict |
|------|---------|-----------|
| Pydantic BaseModel | `model_dump()` | `model_validate(data)` |
| SQLAlchemy ORM | колонки через mapper | `Model(**filtered_dict)` |
| datetime | ISO string + "Z" | `fromisoformat()` |
| list/dict | рекурсивно | — |

Используется в:
- **database_client** — сериализация params и десериализация `data`
- **database_service** — `model_data` → ORM, ORM → dict
- **database_service base_service** — audit (old_data, new_data)
- **paginated_list** — `response_schema(**Converter.to_dict(m))` для items без enricher

---

## 8. Разделение схем и ORM

| Слой | Использует |
|------|------------|
| web_service | shared.schemas (Pydantic) |
| bot_service | shared.schemas (Pydantic) |
| database_service | models/* (SQLAlchemy ORM) |
| db_client при вызове | params: dict (сериализованные) |
| db_client при ответе | model_class=Schema → Pydantic |

**Итого:** ORM живёт только в database_service. Все остальные сервисы работают со схемами.

---

## 9. Типичные костыли (устранены)

- ~~`hasattr(m, "model_dump")`~~ → всегда Pydantic при текущей архитектуре
- ~~`getattr(obj, "id", None)`~~ → `obj.id` у схем
- ~~передача ORM между сервисами~~ → только схемы и dict

Допустимые `dict`:
- RPC envelope: `{success, data, error}`
- `current_user` из JWT
- Storage в callback (например, `GUEST_PARKING_DATA`)
- Фильтры/сортировка (`filters`, `sort`)
