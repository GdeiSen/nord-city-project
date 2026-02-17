import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"
import { TICKET_STATUS_LABELS_RU, TICKET_PRIORITY_LABELS_RU } from "@/types"

export const serviceTicketColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", nullable: false, searchDbColumns: ["id"] },
  {
    id: "ticket",
    label: "Заявка",
    type: "string",
    filterDbColumn: "description",
    searchDbColumns: ["description", "location", "msid"],
  },
  { id: "user", label: "Пользователь", filterDbColumn: "user_id", filterPicker: "users", searchDbColumns: [] },
  { id: "object", label: "Объект", filterDbColumn: "object_id", filterPicker: "objects", searchDbColumns: [] },
  {
    id: "status",
    label: "Статус",
    type: "string",
    searchDbColumns: ["status"],
    filterSelect: Object.entries(TICKET_STATUS_LABELS_RU).map(([value, label]) => ({ value, label })),
  },
  {
    id: "priority",
    label: "Приоритет",
    type: "number",
    searchDbColumns: ["priority"],
    filterSelect: Object.entries(TICKET_PRIORITY_LABELS_RU).map(([value, label]) => ({
      value: String(value),
      label,
    })),
  },
  { id: "category", label: "Категория", type: "string", searchDbColumns: ["category"] },
  {
    id: "created",
    label: "Создана",
    type: "date",
    filterDbColumn: "created_at",
    searchDbColumns: ["created_at"],
  },
]

export const serviceTicketColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  serviceTicketColumns.map((c) => [c.id, configToMeta(c)])
)
