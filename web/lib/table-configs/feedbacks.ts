import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const feedbackColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", searchDbColumns: ["id"] },
  {
    id: "type",
    label: "Тип",
    filterDbColumn: "feedback_type",
    searchDbColumns: ["feedback_type"],
  },
  {
    id: "ticket",
    label: "Заявка",
    searchDbColumns: [],
  },
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
    searchDbColumns: ["answer", "text", "ddid"],
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
