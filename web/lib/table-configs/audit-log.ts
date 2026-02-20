import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

const AUDIT_ENTITY_TYPES = [
  { value: "ServiceTicket", label: "Заявка" },
  { value: "GuestParkingRequest", label: "Гостевая парковка" },
  { value: "User", label: "Пользователь" },
  { value: "Feedback", label: "Отзыв" },
  { value: "Object", label: "Объект" },
  { value: "Space", label: "Помещение" },
  { value: "SpaceView", label: "Просмотр помещения" },
  { value: "PollAnswer", label: "Ответ опроса" },
]

const AUDIT_ACTIONS = [
  { value: "create", label: "Создание" },
  { value: "update", label: "Изменение" },
  { value: "delete", label: "Удаление" },
]

export const auditLogColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", searchDbColumns: ["id"] },
  {
    id: "entity_type",
    label: "Тип сущности",
    type: "string",
    searchDbColumns: ["entity_type"],
    filterSelect: AUDIT_ENTITY_TYPES,
  },
  {
    id: "entity_id",
    label: "ID сущности",
    type: "number",
    searchDbColumns: ["entity_id"],
  },
  {
    id: "action",
    label: "Действие",
    type: "string",
    searchDbColumns: ["action"],
    filterSelect: AUDIT_ACTIONS,
  },
  {
    id: "assignee_display",
    label: "Исполнитель",
    type: "string",
    searchDbColumns: [],
  },
  {
    id: "created",
    label: "Дата",
    type: "date",
    filterDbColumn: "created_at",
    searchDbColumns: ["created_at"],
  },
]

export const auditLogColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  auditLogColumns.map((c) => [c.id, configToMeta(c)])
)
