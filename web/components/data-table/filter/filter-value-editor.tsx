"use client"

import * as React from "react"
import { IconCalendar } from "@tabler/icons-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { EntityPicker } from "@/components/entity-picker"
import { parse } from "date-fns"
import { ru } from "date-fns/locale"
import {
  needsValue,
  isDatetimeValueOperator,
} from "./filter-config"
import type { FilterColumnConfig } from "./filter-config"
import type { FilterOperator } from "@/types/filters"
import type { FilterPickerData } from "@/hooks"

function toDateString(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function parseDateInput(input: string): Date | null {
  const s = input.trim()
  if (!s) return null
  const formats = ["dd.MM.yyyy", "yyyy-MM-dd", "d.M.yyyy", "dd.MM.yy"]
  for (const fmt of formats) {
    try {
      const d = parse(s, fmt, new Date(), { locale: ru })
      if (!isNaN(d.getTime())) return d
    } catch {
      // skip
    }
  }
  const parsed = new Date(s)
  return !isNaN(parsed.getTime()) ? parsed : null
}

export interface FilterValueEditorProps {
  config: FilterColumnConfig
  operator: FilterOperator
  value: string
  dateFrom?: string
  dateTo?: string
  onChange: (updates: { value?: string; dateFrom?: string; dateTo?: string }) => void
  filterPickerData?: FilterPickerData
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function FilterValueEditor({
  config,
  operator,
  value,
  dateFrom,
  dateTo,
  onChange,
  filterPickerData,
  open,
  onOpenChange,
}: FilterValueEditorProps) {
  if (!needsValue(operator)) {
    return null
  }

  switch (config.kind) {
    case "numeric":
      return (
        <Input
          placeholder="Значение..."
          value={value}
          onChange={(e) => onChange({ value: e.target.value })}
          className="h-8 w-full"
          type="number"
        />
      )

    case "text":
      return (
        <Input
          placeholder={
            operator === "matchesRegex"
              ? "Regex, напр. ^test|demo"
              : "Текст..."
          }
          value={value}
          onChange={(e) => onChange({ value: e.target.value })}
          className="h-8 w-full"
          type="text"
        />
      )

    case "relation": {
      const pickerData =
        config.relationType === "users"
          ? filterPickerData?.users
          : filterPickerData?.objects
      if (!pickerData) return null
      const options = (pickerData as { id: number; first_name?: string; last_name?: string; username?: string; name?: string }[]).map((item) => ({
        value: String(item.id),
        label:
          config.relationType === "users"
            ? `${(item.last_name ?? "")} ${(item.first_name ?? "")} @${item.username ?? ""}`.trim() ||
              `#${item.id}`
            : String(item.name ?? `#${item.id}`),
      }))
      return (
        <EntityPicker
          multiple
          options={options}
          value={value}
          onChange={(v) => onChange({ value: v })}
          placeholder={
            config.relationType === "users"
              ? "Выберите пользователей"
              : "Выберите объекты"
          }
        />
      )
    }

    case "select": {
      return (
        <EntityPicker
          multiple
          options={config.options}
          value={value}
          onChange={(v) => onChange({ value: v })}
          placeholder="Выберите..."
        />
      )
    }

    case "datetime": {
      if (!isDatetimeValueOperator(operator)) return null
      const dateStr = value ? (value.includes("T") ? value.slice(0, 10) : value) : ""
      const parsedDate = dateStr
        ? (() => {
            const parts = dateStr.split("-").map(Number)
            if (parts.length >= 3 && !parts.some(isNaN))
              return new Date(parts[0], parts[1] - 1, parts[2])
            const d = new Date(dateStr)
            return !isNaN(d.getTime()) ? d : null
          })()
        : null
      const isValidDate = parsedDate && !isNaN(parsedDate.getTime())
      return (
        <div className="flex gap-1 w-full">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="h-8 shrink-0"
                size="icon"
                type="button"
                aria-label="Календарь"
              >
                <IconCalendar className="h-4 w-4" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                locale={ru}
                selected={isValidDate ? parsedDate : undefined}
                onSelect={(d) =>
                  onChange({ value: d ? toDateString(d) : "" })
                }
                initialFocus
              />
            </PopoverContent>
          </Popover>
          <Input
            placeholder="дд.мм.гггг или гггг-мм-дд"
            value={value}
            onChange={(e) => {
              const v = e.target.value
              onChange({ value: v })
            }}
            onBlur={(e) => {
              const v = e.target.value.trim()
              if (!v) return
              const d = parseDateInput(v)
              if (d) onChange({ value: toDateString(d) })
            }}
            className="h-8 flex-1"
            type="text"
          />
        </div>
      )
    }
    default:
      return (
        <Input
          placeholder="Значение..."
          value={value}
          onChange={(e) => onChange({ value: e.target.value })}
          className="h-8 w-full"
          type="text"
        />
      )
  }
}
