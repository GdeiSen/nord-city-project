# Модели запроса и ответа

Для каждого эндпоинта явно задаётся, что приходит в теле запроса и что возвращается в ответе. Важно разделение: между сервисами передаются базовые модели со всеми полями; для работы сайта используются отдельные request/response DTO, согласованные с API фронта в web/.

**Два слоя моделей.**

Между сервисами (database_service, bot_service, web_service) по HTTP передаются данные в формате, совпадающем с вашими базовыми сущностями: полный набор полей, без искусственного разделения на «только для создания» или «только для ответа» на уровне транспорта. То есть при вызове database_service из web или бота в теле запроса и в ответе используются те же структуры (словари или модели с полным набором полей), которые уже есть в shared (модели БД, DTO или их сериализация). Это упрощает контракт между сервисами и избавляет от лишних преобразований. Для работы сайта (эндпоинты, которые вызывает фронт) отдельно определяются request- и response-DTO: что именно фронт отправляет в теле запроса и что ожидает в ответе. Эти DTO должны соответствовать контракту API, которым пользуется фронт. Контракт задаётся в web/: в web/lib/api.ts видны все вызовы (userApi.getAll, getById, create, update, delete, serviceTicketApi.getByMsid, getStats, rentalSpaceApi.getByObjectId и т.д.) и типы аргументов и возвращаемых значений; в web/types/index.ts описаны интерфейсы User, RentalObject, RentalSpace, ServiceTicket, ServiceTicketLog, Feedback, PollAnswer, RentalSpaceView, а также BaseEntity (id, created_at, updated_at), TicketStats и др. Request/response DTO в web_service нужно спроектировать так, чтобы поля и форматы совпадали с тем, что ожидает фронт: например, create принимает данные без id и дат (аналог Omit<Entity, 'id' | 'created_at' | 'updated_at'> в api.ts), update — частичные поля (Partial<Entity>), ответы — сущность или список с полями из types. Тогда фронт не придётся менять, а контракт API будет явно зафиксирован в DTO.

**Создание (POST).** Тело запроса не должно требовать id, created_at, updated_at. Используется либо отдельная модель CreateResourceRequest с полями, которые фронт реально отправляет (по api.ts и types), либо DTO с опциональными id и датами. Рекомендуется model_config = {"extra": "forbid"}. Ответ — созданная сущность, response_model=ResourceDTO; данные берутся из response["data"] после вызова db_client. Поля response-DTO должны совпадать с интерфейсами в web/types (User, ServiceTicket и т.д.), чтобы JSON корректно десериализовался на фронте.

**Чтение (GET).** Отдельная request-модель не нужна; id или user_id в path задаются параметрами обработчика. Ответ: один DTO или List[DTO]. Типы из shared, при этом структура полей должна соответствовать web/types для сущностей, которые отдаются сайту.

**Обновление (PUT).** Тело — частичное обновление: модель UpdateResourceBody, все поля Optional (как Partial в api.ts). В обработчике в db_client передаётся только переданное: model_dump(exclude_unset=True). В ответ — MessageResponse(message="Resource updated successfully", id=id).

**Удаление (DELETE).** Тела нет; ответ 204 без тела.

**Общие схемы.** В api/schemas/common.py: MessageResponse(message: str, id: int). При необходимости ErrorDetail(detail, code); чаще достаточно HTTPException.

**Кастомные ответы.** Для GET /service-tickets/stats — модель ServiceTicketsStatsResponse с полями total_count, new_count, in_progress_count, completed_count, new_tickets, in_progress_tickets, completed_tickets (списки int). Фронт в api.ts вызывает getStats() и ожидает объект; в web/types есть TicketStats с другой структурой — для эндпоинта stats достаточно совпадать с тем, что реально возвращает backend (ServiceTicketsStats в shared/entities). Остальные кастомные эндпоинты (msid, rental-objects по object_id) возвращают List[ServiceTicketDTO] и List[SpaceDTO]; фронт getByMsid ожидает один ServiceTicket — на бэкенде можно оставить список и на фронте брать первый элемент или изменить контракт по согласованию.

**Auth.** У auth первичный ключ — user_id; в путях /auth/{user_id}. Create/Update-модели учитывают это (user_id не меняется при update). В web/types UserAuth не экспортирован в api.ts (закомментирован), но при включении auth API поля DTO должны совпадать с ожидаемыми фронтом.

**Валидация.** extra="forbid" на request-моделях уменьшает риск лишних полей. Для числовых ограничений при необходимости используют Field(gt=0) и т.п. в Pydantic.

**Итог.** Между сервисами — базовые модели со всеми полями; для сайта — request/response DTO с учётом web/lib/api.ts и web/types/index.ts. Так контракт API явно задан в коде и в OpenAPI, без бесконечной сериализации в разные промежуточные модели.
