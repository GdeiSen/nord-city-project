"use client"

import * as React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"
import {
  format,
  startOfWeek,
  startOfMonth,
  startOfYear,
  startOfDay,
  endOfWeek,
  endOfMonth,
  endOfYear,
  endOfDay,
  subWeeks,
  subMonths,
  subYears,
  addDays,
  addWeeks,
  addMonths,
  addYears,
  parseISO,
  isBefore,
  isAfter,
} from "date-fns"
import { ru } from "date-fns/locale"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import {
  serviceTicketApi,
  userApi,
  feedbackApi,
  rentalSpaceApi,
  rentalObjectApi,
} from "@/lib/api"
import { ChartToolbar } from "./toolbar/chart-toolbar"
import type {
  ChartConfig,
  ChartPeriod,
  ChartEntity,
  ChartMetric,
  ChartDataPoint,
} from "./types"

function getDefaultAnchorDate(): string {
  return format(new Date(), "yyyy-MM-dd")
}

const DEFAULT_CONFIG: ChartConfig = {
  period: "week",
  anchorDate: getDefaultAnchorDate(),
  entity: "service_tickets",
  metric: "count",
  aggregation: "count",
}

function getDateKey(date: Date, period: ChartPeriod): string {
  switch (period) {
    case "day":
      return format(startOfDay(date), "yyyy-MM-dd")
    case "week":
      return format(startOfWeek(date, { weekStartsOn: 1 }), "yyyy-MM-dd")
    case "month":
      return format(startOfMonth(date), "yyyy-MM-dd")
    case "year":
      return format(startOfYear(date), "yyyy-MM-dd")
    default:
      return format(startOfWeek(date, { weekStartsOn: 1 }), "yyyy-MM-dd")
  }
}

function formatLabel(dateStr: string, period: ChartPeriod): string {
  const d = parseISO(dateStr)
  switch (period) {
    case "day":
      return format(d, "d MMM", { locale: ru })
    case "week":
      return format(d, "d MMM", { locale: ru })
    case "month":
      return format(d, "LLL yyyy", { locale: ru })
    case "year":
      return format(d, "yyyy", { locale: ru })
    default:
      return format(d, "d MMM", { locale: ru })
  }
}

/** Get [rangeStart, rangeEnd] for data filtering based on anchor and period */
function getDateRange(anchorDate: string, period: ChartPeriod): [Date, Date] {
  const anchor = parseISO(anchorDate)
  let rangeEnd: Date
  let rangeStart: Date
  switch (period) {
    case "day":
      rangeStart = startOfDay(subWeeks(anchor, 3))
      rangeEnd = endOfDay(anchor)
      break
    case "week":
      rangeEnd = endOfWeek(anchor, { weekStartsOn: 1 })
      rangeStart = subWeeks(startOfWeek(anchor, { weekStartsOn: 1 }), 11)
      break
    case "month":
      rangeEnd = endOfMonth(anchor)
      rangeStart = subMonths(startOfMonth(anchor), 11)
      break
    case "year":
      rangeEnd = endOfYear(anchor)
      rangeStart = subYears(startOfYear(anchor), 4)
      break
    default:
      rangeEnd = endOfWeek(anchor, { weekStartsOn: 1 })
      rangeStart = subWeeks(startOfWeek(anchor, { weekStartsOn: 1 }), 11)
  }
  return [rangeStart, rangeEnd]
}

/** Generate all bucket keys in the date range for full timeline (including empty periods) */
function getAllBucketKeys(rangeStart: Date, rangeEnd: Date, period: ChartPeriod): string[] {
  const keys: string[] = []
  const rangeEndStr = format(rangeEnd, "yyyy-MM-dd")
  let current = rangeStart

  while (true) {
    const currentStr = format(current, "yyyy-MM-dd")
    // Break when we've passed rangeEnd (strictly after; rangeEnd is inclusive)
    if (period === "day" ? currentStr > rangeEndStr : isAfter(current, rangeEnd)) break
    keys.push(getDateKey(current, period))
    switch (period) {
      case "day":
        current = addDays(current, 1)
        break
      case "week":
        current = addWeeks(current, 1)
        break
      case "month":
        current = addMonths(current, 1)
        break
      case "year":
        current = addYears(current, 1)
        break
      default:
        current = addWeeks(current, 1)
    }
  }
  return keys
}

async function fetchEntityData(
  entity: ChartEntity
): Promise<Array<Record<string, unknown>>> {
  switch (entity) {
    case "service_tickets":
      return serviceTicketApi.getAll()
    case "users":
      return userApi.getAll()
    case "feedbacks":
      return feedbackApi.getAll()
    case "rental_spaces":
      return rentalSpaceApi.getAll()
    case "rental_objects":
      return rentalObjectApi.getAll()
    default:
      return []
  }
}

function aggregateData(
  items: Array<Record<string, unknown>>,
  config: ChartConfig
): ChartDataPoint[] {
  const { period, metric, aggregation, anchorDate } = config
  const [rangeStart, rangeEnd] = getDateRange(anchorDate, period)
  const buckets = new Map<string, { count: number; sum: number }>()

  for (const item of items) {
    const createdAt = item.created_at
    if (typeof createdAt !== "string") continue

    const date = parseISO(createdAt)
    if (isBefore(date, rangeStart) || isAfter(date, rangeEnd)) continue

    const key = getDateKey(date, period)

    const current = buckets.get(key) ?? { count: 0, sum: 0 }
    current.count += 1

    if (metric === "size" && typeof item.size === "number") {
      current.sum += item.size
    }

    buckets.set(key, current)
  }

  // Use full timeline (all periods in range) so line chart shows continuous data
  const allKeys = getAllBucketKeys(rangeStart, rangeEnd, period)
  return allKeys.map((key) => {
    const bucket = buckets.get(key) ?? { count: 0, sum: 0 }
    const { count, sum } = bucket
    let value: number
    if (metric === "size") {
      value = aggregation === "avg" ? (count > 0 ? sum / count : 0) : sum
    } else {
      value = count
    }
    return {
      label: formatLabel(key, period),
      value: Math.round(value * 100) / 100,
      date: key,
    }
  })
}


export interface DashboardChartProps {
  /** Initial config (optional) */
  defaultConfig?: Partial<ChartConfig>
  /** Custom class name for the card */
  className?: string
}

export function DashboardChart({
  defaultConfig,
  className,
}: DashboardChartProps) {
  const [config, setConfig] = React.useState<ChartConfig>({
    ...DEFAULT_CONFIG,
    ...defaultConfig,
    anchorDate: defaultConfig?.anchorDate ?? getDefaultAnchorDate(),
  })
  const [data, setData] = React.useState<ChartDataPoint[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  const effectiveConfig = React.useMemo(
    () => ({
      ...config,
      metric: "count" as ChartMetric,
      aggregation: "count" as const,
      anchorDate: config.anchorDate || getDefaultAnchorDate(),
    }),
    [config]
  )

  const fetchData = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const items = await fetchEntityData(config.entity)
      const aggregated = aggregateData(items, effectiveConfig)
      setData(aggregated)
    } catch (e: any) {
      setError(e?.message ?? "Не удалось загрузить данные")
      setData([])
    } finally {
      setLoading(false)
    }
  }, [config.entity, effectiveConfig])

  React.useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleConfigChange = React.useCallback((updates: Partial<ChartConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }))
  }, [])

  const chartTitle = React.useMemo(() => {
    const entityLabels: Record<ChartEntity, string> = {
      service_tickets: "Заявки",
      users: "Пользователи",
      feedbacks: "Отзывы",
      rental_spaces: "Помещения",
      rental_objects: "Бизнес-центры",
    }
    const periodLabels: Record<ChartPeriod, string> = {
      day: "по дням",
      week: "по неделям",
      month: "по месяцам",
      year: "по годам",
    }
    return `${entityLabels[config.entity]} — Количество ${periodLabels[config.period]}`
  }, [config.entity, config.period])

  return (
    <Card className={className}>
      <CardHeader className="space-y-0 pb-2">
        <h3 className="text-sm font-medium">{chartTitle}</h3>
      </CardHeader>
      <CardContent className="h-[300px]">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Spinner className="h-8 w-8" />
          </div>
        ) : error ? (
          <div className="flex h-full items-center justify-center text-sm text-destructive">
            {error}
          </div>
        ) : data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Нет данных за выбранный период
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                interval={config.period === "day" ? 0 : "preserveStartEnd"}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
                domain={[0, "auto"]}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: "var(--radius)",
                  border: "1px solid hsl(var(--border))",
                }}
                formatter={(value: number | undefined) => [value ?? 0, "Значение"]}
                labelFormatter={(label) => `Период: ${label}`}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--foreground)"
                strokeWidth={2}
                dot={{ fill: "var(--foreground)", strokeWidth: 0, r: 3 }}
                activeDot={{ r: 4 }}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
      <div className="border-t px-6 pt-6">
        <ChartToolbar
          config={config}
          onConfigChange={handleConfigChange}
        />
      </div>
    </Card>
  )
}
