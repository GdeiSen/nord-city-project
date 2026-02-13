# Явное API в web_service

Маршруты перестают генерироваться через BaseApiRouter. Каждый эндпоинт задаётся отдельным обработчиком с явными типами запроса и ответа. Уходит сложная цепочка сериализации: один входной тип на эндпоинт, один выходной, вызов db_client и при необходимости HTTPException. Все API-маршруты под префиксом /api/v1; в main подключаются только явные роутеры.

**Полная таблица эндпоинтов.**

Пути указаны относительно префикса /api/v1. Колонки: Метод, Путь, Тело запроса, Ответ, Вызов — метод db_client.

| Ресурс | Метод | Путь | Тело | Ответ | Вызов |
|--------|-------|------|------|--------|--------|
| Users | POST | /users/ | CreateUserRequest | UserDTO 201 | db_client.user.create(model_data=...) |
| Users | GET | /users/ | — | List[UserDTO] | db_client.user.get_all() |
| Users | GET | /users/{id} | — | UserDTO | db_client.user.get_by_id(entity_id=id) |
| Users | PUT | /users/{id} | UpdateUserBody | MessageResponse | db_client.user.update(...) |
| Users | DELETE | /users/{id} | — | 204 | db_client.user.delete(...) |
| Auth | POST | /auth | CreateAuthRequest | UserAuthDTO 201 | db_client.auth.create(...) |
| Auth | GET | /auth | — | List[UserAuthDTO] | db_client.auth.get_all() |
| Auth | GET | /auth/{user_id} | — | UserAuthDTO | db_client.auth.get_by_id(entity_id=user_id) |
| Auth | PUT | /auth/{user_id} | UpdateAuthBody | MessageResponse | db_client.auth.update(...) |
| Auth | DELETE | /auth/{user_id} | — | 204 | db_client.auth.delete(...) |
| Feedbacks | POST | /feedbacks/ | CreateFeedbackRequest | FeedbackDTO 201 | db_client.feedback.create(...) |
| Feedbacks | GET | /feedbacks/ | — | List[FeedbackDTO] | db_client.feedback.get_all() |
| Feedbacks | GET | /feedbacks/{id} | — | FeedbackDTO | db_client.feedback.get_by_id(...) |
| Feedbacks | PUT | /feedbacks/{id} | UpdateFeedbackBody | MessageResponse | db_client.feedback.update(...) |
| Feedbacks | DELETE | /feedbacks/{id} | — | 204 | db_client.feedback.delete(...) |
| Rental objects | POST | /rental-objects/ | CreateObjectRequest | ObjectDTO 201 | db_client.object.create(...) |
| Rental objects | GET | /rental-objects/ | — | List[ObjectDTO] | db_client.object.get_all() |
| Rental objects | GET | /rental-objects/{id} | — | ObjectDTO | db_client.object.get_by_id(...) |
| Rental objects | PUT | /rental-objects/{id} | UpdateObjectBody | MessageResponse | db_client.object.update(...) |
| Rental objects | DELETE | /rental-objects/{id} | — | 204 | db_client.object.delete(...) |
| Polls | POST | /polls/ | CreatePollRequest | PollAnswerDTO 201 | db_client.poll.create(...) |
| Polls | GET | /polls/ | — | List[PollAnswerDTO] | db_client.poll.get_all() |
| Polls | GET | /polls/{id} | — | PollAnswerDTO | db_client.poll.get_by_id(...) |
| Polls | PUT | /polls/{id} | UpdatePollBody | MessageResponse | db_client.poll.update(...) |
| Polls | DELETE | /polls/{id} | — | 204 | db_client.poll.delete(...) |
| Service tickets | POST | /service-tickets/ | CreateServiceTicketRequest | ServiceTicketDTO 201 | db_client.service_ticket.create(...) |
| Service tickets | GET | /service-tickets/ | — | List[ServiceTicketDTO] | db_client.service_ticket.get_all() |
| Service tickets | GET | /service-tickets/{id} | — | ServiceTicketDTO | db_client.service_ticket.get_by_id(...) |
| Service tickets | PUT | /service-tickets/{id} | UpdateServiceTicketBody | MessageResponse | db_client.service_ticket.update(...) |
| Service tickets | DELETE | /service-tickets/{id} | — | 204 | db_client.service_ticket.delete(...) |
| Service tickets | GET | /service-tickets/msid/{msid} | — | List[ServiceTicketDTO] | db_client.service_ticket.find(filters={'msid': msid}) |
| Service tickets | GET | /service-tickets/stats | — | ServiceTicketsStatsResponse | db_client.service_ticket.get_stats() |
| Service ticket logs | POST | /service-ticket-logs/ | CreateLogRequest | ServiceTicketLogDTO 201 | db_client.service_ticket_log.create(...) |
| Service ticket logs | GET | /service-ticket-logs/ | — | List[ServiceTicketLogDTO] | db_client.service_ticket_log.get_all() |
| Service ticket logs | GET | /service-ticket-logs/{id} | — | ServiceTicketLogDTO | db_client.service_ticket_log.get_by_id(...) |
| Service ticket logs | PUT | /service-ticket-logs/{id} | UpdateLogBody | MessageResponse | db_client.service_ticket_log.update(...) |
| Service ticket logs | DELETE | /service-ticket-logs/{id} | — | 204 | db_client.service_ticket_log.delete(...) |
| Rental spaces | POST | /rental-spaces/ | CreateSpaceRequest | SpaceDTO 201 | db_client.space.create(...) |
| Rental spaces | GET | /rental-spaces/ | — | List[SpaceDTO] | db_client.space.get_all() |
| Rental spaces | GET | /rental-spaces/{id} | — | SpaceDTO | db_client.space.get_by_id(...) |
| Rental spaces | PUT | /rental-spaces/{id} | UpdateSpaceBody | MessageResponse | db_client.space.update(...) |
| Rental spaces | DELETE | /rental-spaces/{id} | — | 204 | db_client.space.delete(...) |
| Rental spaces | GET | /rental-spaces/rental-objects/{object_id} | — | List[SpaceDTO] | db_client.space.find(filters={'object_id': object_id}) |
| Space views | POST | /space-views/ | CreateSpaceViewRequest | SpaceViewDTO 201 | db_client.space_view.create(...) |
| Space views | GET | /space-views/ | — | List[SpaceViewDTO] | db_client.space_view.get_all() |
| Space views | GET | /space-views/{id} | — | SpaceViewDTO | db_client.space_view.get_by_id(...) |
| Space views | PUT | /space-views/{id} | UpdateSpaceViewBody | MessageResponse | db_client.space_view.update(...) |
| Space views | DELETE | /space-views/{id} | — | 204 | db_client.space_view.delete(...) |
| Служебные | GET | / | — | HTML | — |
| Служебные | GET | /health | — | JSON status | — |

Кратко по ресурсам. Users — /users. POST / — тело: создание пользователя (request DTO), ответ: UserDTO (201). GET / — список UserDTO. GET /{id} — один UserDTO. PUT /{id} — тело: частичное обновление (UpdateUserBody), ответ: MessageResponse. DELETE /{id} — ответ 204. Вызовы: db_client.user.create(model_data=...), get_all(), get_by_id(entity_id=id), update(entity_id=id, update_data=...), delete(entity_id=id).

Auth — /auth. Первичный ключ сущности auth — user_id; в путях используется {user_id}. POST / — создание (UserAuthDTO или request DTO), ответ UserAuthDTO (201). GET / — список UserAuthDTO. GET /{user_id} — один UserAuthDTO. PUT /{user_id} — частичное обновление, ответ MessageResponse. DELETE /{user_id} — 204. Вызовы: db_client.auth.create(...), get_all(), get_by_id(entity_id=user_id), update(entity_id=user_id, ...), delete(entity_id=user_id).

Feedbacks — /feedbacks. POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}. Тела и ответы по тому же принципу (FeedbackDTO, CreateFeedbackRequest, UpdateFeedbackBody, MessageResponse, 204). Вызовы: db_client.feedback.*.

Rental objects — /rental-objects. POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}. ObjectDTO и соответствующие request/update модели. Вызовы: db_client.object.*.

Polls — /polls. POST /, GET /, GET /{id}, PUT /{id}, DELETE /{id}. PollAnswerDTO и т.д. Вызовы: db_client.poll.*.

Service tickets — /service-tickets. CRUD как выше (ServiceTicketDTO, Create, Update, MessageResponse, 204). Дополнительно: GET /msid/{msid} — ответ List[ServiceTicketDTO], вызов db_client.service_ticket.find(filters={'msid': msid}). GET /stats — ответ ServiceTicketsStatsResponse (total_count, new_count, in_progress_count, completed_count, new_tickets, in_progress_tickets, completed_tickets), вызов db_client.service_ticket.get_stats(). Вызовы CRUD: db_client.service_ticket.create, get_all, get_by_id, update, delete.

Service ticket logs — /service-ticket-logs. CRUD, ServiceTicketLogDTO и request/update модели. Вызовы: db_client.service_ticket_log.*.

Rental spaces — /rental-spaces. CRUD (SpaceDTO и т.д.). Дополнительно: GET /rental-objects/{object_id} — ответ List[SpaceDTO], вызов db_client.space.find(filters={'object_id': object_id}). Вызовы: db_client.space.*.

Space views — /space-views. CRUD, SpaceViewDTO. Вызовы: db_client.space_view.*.

Служебные (вне /api/v1). GET / — HTML-страница со ссылкой на /docs. GET /health — JSON: status, service, database_client_connected (или аналог).

**Обработка ошибок.**

Если db_client возвращает success: false, обработчик поднимает HTTPException: при фразе типа "not found" в error — 404, при ошибке валидации — 400, иначе по ситуации; в detail передаётся error из ответа.

**Структура кода.**

В api/schemas/ — модели запроса и ответа: common.py (MessageResponse), по ресурсам — CreateResourceRequest, UpdateResourceBody, при необходимости отдельные response-модели (например ServiceTicketsStatsResponse). В api/routers/ — по модулю на ресурс (users.py, auth.py, feedbacks.py, rental_objects.py, polls.py, service_tickets.py с msid и stats, service_ticket_logs.py, rental_spaces.py с rental-objects/{object_id}, space_views.py). В каждом роутере явно объявлены маршруты с указанием response_model и body. В обработчике: вызов db_client, разбор ответа, возврат данных в виде, ожидаемом response_model, или raise HTTPException. Без BaseApiRouter и без цепочек сериализации через несколько промежуточных моделей.
