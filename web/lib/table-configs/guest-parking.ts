import type { DataTableColumnMeta } from "@/components/data-table"
import type { TableColumnConfig } from "./types"
import { configToMeta } from "./types"

export const guestParkingColumns: TableColumnConfig[] = [
  { id: "id", label: "ID", type: "number", nullable: false, searchDbColumns: ["id"] },
  {
    id: "arrival",
    label: "Дата и время заезда",
    type: "date",
    filterDbColumn: "arrival_date",
    searchDbColumns: ["arrival_date"],
  },
  { id: "license_plate", label: "Госномер", type: "string", searchDbColumns: ["license_plate"] },
  { id: "car_make_color", label: "Марка и цвет", type: "string", searchDbColumns: ["car_make_color"] },
  { id: "driver_phone", label: "Телефон водителя", type: "string", searchDbColumns: ["driver_phone"] },
  { id: "user", label: "Арендатор", filterDbColumn: "user_id", filterPicker: "users", searchDbColumns: [] },
]

export const guestParkingColumnMeta: Record<string, DataTableColumnMeta> = Object.fromEntries(
  guestParkingColumns.map((c) => [c.id, configToMeta(c)])
)
