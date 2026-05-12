import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const guestParkingColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", nullable: false, searchDbColumns: ["id"] },
  {
    id: "arrival",
    label: "Интервал заезда",
    type: "date",
    filterDbColumn: "arrival_start_at",
    searchDbColumns: ["arrival_start_at", "arrival_end_at"],
  },
  {
    id: "status",
    label: "Статус",
    type: "string",
    filterDbColumn: "status",
    searchDbColumns: ["status"],
    filterSelect: [
      { value: "NEW", label: "Ожидает" },
      { value: "APPROVED", label: "Подтверждена" },
      { value: "REJECTED", label: "Отклонена" },
    ],
  },
  { id: "license_plate", label: "Госномер", type: "string", searchDbColumns: ["license_plate"] },
  { id: "car_make_color", label: "Марка и цвет", type: "string", searchDbColumns: ["car_make_color"] },
  { id: "user", label: "Арендатор", filterDbColumn: "user_id", filterPicker: "users", searchDbColumns: [] },
]

export const guestParkingColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  guestParkingColumns.map((c) => [c.id, configToMeta(c)])
)
