import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const feedbackColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", searchDbColumns: ["id"] },
  {
    id: "user",
    label: "Пользователь",
    filterDbColumn: "user_id",
    filterPicker: "users",
    searchDbColumns: [],
  },
  {
    id: "feedback",
    label: "Отзыв",
    type: "string",
    filterDbColumn: "answer",
    searchDbColumns: ["answer", "ddid"],
  },
  {
    id: "date",
    label: "Дата",
    type: "date",
    filterDbColumn: "created_at",
    searchDbColumns: ["created_at"],
  },
]

export const feedbackColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  feedbackColumns.map((c) => [c.id, configToMeta(c)])
)
