# Nord City Media Service

Сервис хранения и раздачи медиа-файлов (изображения, документы).

## Назначение

- **Хранение** — файлы сохраняются на диск в настраиваемую директорию
- **Раздача** — доступ к файлам по HTTP URL
- **Загрузка** — приём файлов через API (proxy через web_service)

## API

| Метод | Путь | Описание |
|-------|------|----------|
| POST | /internal/rpc | RPC‑эндпоинт для MediaClient (service=media, methods: upload, delete) |
| POST | /upload | Загрузка файла (multipart, поле `file`) — для прямых запросов |
| GET | /media/{path} | Получить файл по пути |
| DELETE | /media/{path} | Удалить файл |
| GET | /health | Проверка работоспособности |

## Конфигурация (переменные окружения)

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| MEDIA_SERVICE_PORT | 8004 | Порт HTTP-сервера |
| MEDIA_SERVICE_HOST | 0.0.0.0 | Хост для биндинга |
| MEDIA_STORAGE_DIR | infrastructure/media_storage | Директория хранения |
| MEDIA_MAX_UPLOAD_SIZE | 10485760 | Макс. размер загрузки (10 MB) |

## Использование из web_service

MediaClient построен на HttpRpcClient (как DatabaseClient) и обращается к `/internal/rpc`:

```python
from shared.clients.media_client import media_client

# Загрузка (RPC: media.upload)
result = await media_client.upload(
    file_content=bytes_data,
    filename="photo.jpg",
    content_type="image/jpeg",
)
# result: {"path": "uuid_photo.jpg", "url": "http://host:8004/media/uuid_photo.jpg"}

# Удаление (RPC: media.delete)
await media_client.delete("uuid_photo.jpg")

# Конструкция URL по пути
url = media_client.get_media_url("uuid_photo.jpg")
```

## Загрузка через web API

Клиент (frontend) загружает файлы через `POST /api/v1/media/upload` (с авторизацией Admin/Super Admin). Ответ содержит полный URL для отображения.
