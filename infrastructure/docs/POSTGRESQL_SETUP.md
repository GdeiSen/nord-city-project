# Запуск и настройка PostgreSQL для проекта Nord City

Краткая инструкция: установка PostgreSQL, создание базы и пользователя, настройка проекта.

---

## 1. Установка PostgreSQL

### Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

Проверка, что сервис запущен:

```bash
sudo systemctl status postgresql
```

Запуск (если не запущен):

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql   # автозапуск при загрузке
```

### Через Docker (альтернатива)

```bash
docker run -d \
  --name nordcity-pg \
  -e POSTGRES_USER=nordcity_app \
  -e POSTGRES_PASSWORD=ваш_надёжный_пароль \
  -e POSTGRES_DB=nordcity_db \
  -p 5432:5432 \
  postgres:16-alpine
```

Если используете Docker, шаги 2 и 3 можно пропустить — база и пользователь уже созданы. Те же значения укажите в `.env` (раздел 4).

---

## 2. Создание пользователя и базы данных

Имена пользователя и базы могут быть любыми. Главное — одни и те же имена и пароль указать в `.env`. Ниже — как называть «по канонам».

### Как назвать по канонам

**Общие правила:**

- **Только строчные буквы и подчёркивания** — в PostgreSQL неэкранированные имена приводятся к нижнему регистру; цифры допустимы. Без дефисов и пробелов (иначе придётся везде кавычить).
- **Имя по проекту/приложению**, не по роли («база для бота»). К одной базе обычно подключаются несколько сервисов (API, воркеры, бот).
- **Кратко и однозначно** — по имени проекта или приложения.

**База данных:**

- Часто имя приложения в lowercase: `nordcity`, `myapp`.
- Вариант с суффиксом: `nordcity_db` — явно «база», удобно, если на одном кластере несколько баз (например `nordcity_db`, `analytics_db`).
- Окружение в имени обычно не обязательно для одной инсталляции; при нескольких (staging/prod) иногда делают `nordcity_staging`, `nordcity_production`.

**Пользователь (роль) PostgreSQL:**

- Отдельная роль на приложение — хорошая практика (минимальные привилегии, не под суперпользователем).
- Имя отражает приложение или назначение: `nordcity_app`, `nordcity_svc` (service), или просто `nordcity` — один пользователь на всё приложение.
- Не использовать `admin`, `root`, `user` для приложения — их оставить для администрирования БД.

**Итого для Nord City (каноничный вариант):**

| Что        | Имя           | Комментарий                    |
|-----------|----------------|---------------------------------|
| База      | `nordcity` или `nordcity_db` | одна база проекта              |
| Роль (user) | `nordcity_app`             | один пользователь для приложения |

В примерах ниже в командах использованы `nordcity_db` и `nordcity_app` — при желании замените на свои (например просто `nordcity` для базы).

Подключитесь к PostgreSQL под суперпользователем `postgres`:

```bash
sudo -u postgres psql
```

В интерактивной консоли `psql` выполните **по шагам** (не вставляйте всё сразу — команда `\connect` должна быть отдельно).

**Шаг 1** — создать роль, базу и выдать права на базу:

```sql
CREATE USER nordcity_app WITH PASSWORD 'ваш_надёжный_пароль';
CREATE DATABASE nordcity_db OWNER nordcity_app;
GRANT ALL PRIVILEGES ON DATABASE nordcity_db TO nordcity_app;
```

**Шаг 2** — переключиться на базу (выполнить одну строку и нажать Enter):

```
\connect nordcity_db
```

**Шаг 3** — выдать права на схему `public` (выполнить в уже подключённой к `nordcity_db` сессии):

```sql
GRANT ALL ON SCHEMA public TO nordcity_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nordcity_app;
```

**Выход из psql:** `\q`

Пароль замените на свой и обязательно продублируйте его в `.env` (см. раздел 4).

---

## 3. Разрешить подключение с локального хоста (опционально)

По умолчанию PostgreSQL принимает подключения по `localhost`. Если подключаетесь с той же машины — менять ничего не нужно.

Если будете подключаться с другого хоста или по IP (например `127.0.0.1` вместо `localhost`), проверьте конфиг:

1. Найти конфиг `pg_hba.conf`:

   ```bash
   sudo -u postgres psql -t -P -A -c "SHOW hba_file"
   ```

2. Добавить строку для доступа по паролю с локального хоста (если её ещё нет). Подставьте свои имя базы и пользователя:

   ```
   # TYPE  DATABASE     USER          ADDRESS         METHOD
   host    nordcity_db  nordcity_app  127.0.0.1/32    scram-sha-256
   host    nordcity_db  nordcity_app  ::1/128         scram-sha-256
   ```

3. Перезапустить PostgreSQL:

   ```bash
   sudo systemctl restart postgresql
   ```

---

## 4. Настройка проекта (.env)

В каталоге `infrastructure` должен быть файл `.env`. Переменные для БД должны **точно совпадать** с именем базы, пользователем и паролем, которые вы задали при создании (шаг 2 или Docker):

```env
# Database Configuration (подставьте свои имя базы, пользователя и пароль)
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=nordcity_db
DB_USER=nordcity_app
DB_PASSWORD=ваш_надёжный_пароль
```

- `DB_HOST` — хост, где запущен PostgreSQL (`127.0.0.1` для локального, при Docker тоже обычно `127.0.0.1`).
- `DB_PORT` — порт (по умолчанию `5432`).
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` — те же имя базы, пользователь и пароль, что при создании в PostgreSQL (или в переменных Docker).

Остальные переменные в `.env` (Telegram, сервисы, CORS и т.д.) оставьте как есть или настройте отдельно.

---

## 5. Проверка подключения

Из каталога `infrastructure` с активированным venv:

```bash
cd /opt/001_project_nord_city/infrastructure
source venv/bin/activate
pip install -r requirements.txt   # если ещё не ставили
```

Проверка через `psql` (подставьте свой пароль, пользователя и базу):

```bash
PGPASSWORD=ваш_пароль psql -h 127.0.0.1 -p 5432 -U nordcity_app -d nordcity_db -c "SELECT 1;"
```

Если команда выполнилась без ошибок — подключение к БД работает.

---

## 6. Запуск проекта и создание таблиц

Таблицы в этом проекте создаются автоматически при старте Database Service (через SQLAlchemy `Base.metadata.create_all`). Отдельные миграции (Alembic) не используются.

1. Активируйте venv и задайте переменные из `.env` (или экспортируйте их вручную):

   ```bash
   cd /opt/001_project_nord_city/infrastructure
   source venv/bin/activate
   export $(grep -v '^#' .env | xargs)   # загрузить .env в текущую оболочку
   ```

2. Запустите оркестратор (он поднимает сервисы, в том числе database_service):

   ```bash
   python orchestrator.py
   ```

При первом запуске Database Service подключится к PostgreSQL и создаст все таблицы. Дальше можно пользоваться приложением как обычно.

---

## 7. Частые проблемы

| Проблема | Что проверить |
|----------|----------------|
| `connection refused` (порт 5432) | Запущен ли PostgreSQL: `sudo systemctl status postgresql` |
| `password authentication failed` | Совпадают ли `DB_USER`/`DB_PASSWORD` в `.env` с пользователем в PostgreSQL |
| `database "..." does not exist` | База создана: `sudo -u postgres psql -l` — в списке должна быть ваша БД |
| `ModuleNotFoundError: dotenv` | Активирован venv и установлены зависимости: `pip install -r requirements.txt` |
| Таблиц нет | Убедиться, что Database Service действительно стартовал и в логах нет ошибок подключения к БД |

---

## Итоговый чек-лист

1. Установлен и запущен PostgreSQL.
2. Созданы пользователь и база (например `nordcity_app` и `nordcity_db`), выданы права.
3. В `infrastructure/.env` заданы `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — те же имена и пароль, что при создании.
4. Подключение проверено: `PGPASSWORD=... psql -h 127.0.0.1 -U <DB_USER> -d <DB_NAME> -c "SELECT 1;"`.
5. Запуск: `source venv/bin/activate`, при необходимости `export` из `.env`, затем `python orchestrator.py`.

После этого база готова к работе с проектом Nord City.
