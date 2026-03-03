import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const storageFileColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", nullable: false, searchDbColumns: ["id"] },
  {
    id: "original_name",
    label: "Файл",
    type: "string",
    filterDbColumn: "original_name",
    searchDbColumns: ["original_name", "storage_path"],
  },
  {
    id: "kind",
    label: "Тип",
    type: "string",
    searchDbColumns: ["kind"],
    filterSelect: [
      { value: "IMAGE", label: "Изображение" },
      { value: "VIDEO", label: "Видео" },
      { value: "DOCUMENT", label: "Документ" },
      { value: "OTHER", label: "Прочее" },
    ],
  },
  {
    id: "category",
    label: "Категория",
    type: "string",
    searchDbColumns: ["category"],
    filterSelect: [
      { value: "DEFAULT", label: "DEFAULT" },
      { value: "SYSTEM", label: "SYSTEM" },
      { value: "TEMP", label: "TEMP" },
    ],
  },
  {
    id: "entity_type",
    label: "Сущность",
    type: "string",
    searchDbColumns: ["entity_type", "entity_id"],
  },
  {
    id: "content_type",
    label: "MIME",
    type: "string",
    searchDbColumns: ["content_type", "extension"],
  },
  {
    id: "created_at",
    label: "Создан",
    type: "date",
    filterDbColumn: "created_at",
    searchDbColumns: ["created_at"],
  },
]

export const storageFileColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  storageFileColumns.map((column) => [column.id, configToMeta(column)])
)
