import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const userColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", searchDbColumns: ["id"] },
  {
    id: "user",
    label: "Пользователь",
    type: "string",
    searchDbColumns: ["first_name", "last_name", "middle_name", "username"],
  },
  {
    id: "contacts",
    label: "Контакты",
    type: "string",
    searchDbColumns: ["email", "phone_number"],
  },
  {
    id: "roles",
    label: "Роли",
    type: "string",
    searchDbColumns: ["roles"],
  },
  {
    id: "object",
    label: "Объект",
    type: "number",
    filterDbColumn: "object_id",
    filterPicker: "objects",
    searchDbColumns: ["object_id"],
  },
  { id: "legal_entity", label: "Юр. лицо", type: "string", searchDbColumns: ["legal_entity"] },
  {
    id: "created",
    label: "Создан",
    type: "date",
    filterDbColumn: "created_at",
    searchDbColumns: ["created_at"],
  },
]

export const userColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  userColumns.map((c) => [c.id, configToMeta(c)])
)
