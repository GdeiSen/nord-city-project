"use client"

import * as React from "react"
import {
  IconCalendar,
  IconChevronLeft,
  IconChevronRight,
  IconTicket,
  IconUsers,
  IconMessageCircle,
  IconBuildingSkyscraper,
  IconLayoutGrid,
} from "@tabler/icons-react"
import { format, parse, parseISO, addDays, addWeeks, addMonths, addYears, subDays, subWeeks, subMonths, subYears } from "date-fns"
import { ru } from "date-fns/locale"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type {
  ChartConfig,
  ChartPeriod,
  ChartEntity,
} from "../types"
import {
  CHART_PERIOD_LABELS,
  CHART_ENTITY_LABELS,
} from "../types"

function toDateString(d: Date): string {
  return format(d, "yyyy-MM-dd")
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
      /* skip */
    }
  }
  const parsed = new Date(s)
  return !isNaN(parsed.getTime()) ? parsed : null
}

const ENTITY_ICONS: Record<ChartEntity, React.ReactNode> = {
  service_tickets: <IconTicket className="h-4 w-4" />,
  users: <IconUsers className="h-4 w-4" />,
  feedbacks: <IconMessageCircle className="h-4 w-4" />,
  rental_spaces: <IconLayoutGrid className="h-4 w-4" />,
  rental_objects: <IconBuildingSkyscraper className="h-4 w-4" />,
}

export interface ChartToolbarProps {
  config: ChartConfig
  onConfigChange: (config: Partial<ChartConfig>) => void
}

function shiftAnchor(anchor: string, period: ChartPeriod, direction: 1 | -1): string {
  const d = parseISO(anchor)
  if (period === "day") {
    return toDateString(direction > 0 ? addDays(d, 1) : subDays(d, 1))
  }
  if (period === "week") {
    return toDateString(direction > 0 ? addWeeks(d, 1) : subWeeks(d, 1))
  }
  if (period === "month") {
    return toDateString(direction > 0 ? addMonths(d, 1) : subMonths(d, 1))
  }
  return toDateString(direction > 0 ? addYears(d, 1) : subYears(d, 1))
}

export function ChartToolbar({
  config,
  onConfigChange,
}: ChartToolbarProps) {
  const [dateInput, setDateInput] = React.useState(
    format(parseISO(config.anchorDate), "dd.MM.yyyy", { locale: ru })
  )

  React.useEffect(() => {
    setDateInput(format(parseISO(config.anchorDate), "dd.MM.yyyy", { locale: ru }))
  }, [config.anchorDate])

  const handleDateChange = React.useCallback(
    (value: string) => {
      setDateInput(value)
      const d = parseDateInput(value)
      if (d) onConfigChange({ anchorDate: toDateString(d) })
    },
    [onConfigChange]
  )

  const handlePrev = () => onConfigChange({ anchorDate: shiftAnchor(config.anchorDate, config.period, -1) })
  const handleNext = () => onConfigChange({ anchorDate: shiftAnchor(config.anchorDate, config.period, 1) })

  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Period: week | month | year */}
      <ToggleGroup
        type="single"
        value={config.period}
        onValueChange={(v) => v && onConfigChange({ period: v as ChartPeriod })}
        variant="outline"
        size="sm"
        className="h-8 justify-start"
      >
        {(Object.keys(CHART_PERIOD_LABELS) as ChartPeriod[]).map((p) => (
          <ToggleGroupItem key={p} value={p} className="h-8 px-3">
            {CHART_PERIOD_LABELS[p]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>

      {/* Date navigation: [calendar] [←] [input] [→] */}
      <div className="flex items-center gap-0 rounded-md border">
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 shrink-0 rounded-r-none border-r"
              aria-label="Календарь"
            >
              <IconCalendar className="h-4 w-4 text-muted-foreground" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              locale={ru}
              selected={parseISO(config.anchorDate)}
              onSelect={(d) => d && onConfigChange({ anchorDate: toDateString(d) })}
              initialFocus
            />
          </PopoverContent>
        </Popover>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 rounded-none"
          onClick={handlePrev}
          aria-label="Предыдущий период"
        >
          <IconChevronLeft className="h-4 w-4" />
        </Button>
        <Input
          placeholder="дд.мм.гггг"
          value={dateInput}
          onChange={(e) => setDateInput(e.target.value)}
          onBlur={() => {
            const d = parseDateInput(dateInput)
            if (d) onConfigChange({ anchorDate: toDateString(d) })
          }}
          onKeyDown={(e) => e.key === "Enter" && handleDateChange(dateInput)}
          className="h-8 w-[120px] border-0 border-x rounded-none bg-transparent text-center text-sm focus-visible:ring-0 focus-visible:ring-offset-0"
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 rounded-l-none"
          onClick={handleNext}
          aria-label="Следующий период"
        >
          <IconChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Entity */}
      <Select
        value={config.entity}
        onValueChange={(v) => onConfigChange({ entity: v as ChartEntity })}
      >
        <SelectTrigger size="sm" className="h-8 w-[180px]">
          <SelectValue placeholder="Сущность" />
        </SelectTrigger>
        <SelectContent>
          {(Object.keys(CHART_ENTITY_LABELS) as ChartEntity[]).map((e) => (
            <SelectItem key={e} value={e}>
              <span className="flex items-center gap-2">
                {ENTITY_ICONS[e]}
                {CHART_ENTITY_LABELS[e]}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

    </div>
  )
}
