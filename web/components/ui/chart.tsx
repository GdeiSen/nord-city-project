"use client"

import * as React from "react"
import * as RechartsPrimitive from "recharts"
import type {
  TooltipProps as RechartsTooltipProps,
  LegendProps as RechartsLegendProps,
  LegendPayload,
} from "recharts"

// Payload type is not exported from recharts v3, so we define it ourselves
type RechartsPayload<TValue, TName> = {
  name?: TName
  value?: TValue
  dataKey?: string | number
  color?: string
  payload?: {
    fill?: string
    [key: string]: unknown
  }
  [key: string]: unknown
}

import { cn } from "@/lib/utils"

// Format: { THEME_NAME: CSS_SELECTOR }
const THEMES = { light: "", dark: ".dark" } as const

export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode
    icon?: React.ComponentType
  } & (
    | { color?: string; theme?: never }
    | { color?: never; theme: Record<keyof typeof THEMES, string> }
  )
}

type ChartContextProps = {
  config: ChartConfig
}

const ChartContext = React.createContext<ChartContextProps | null>(null)

function useChart() {
  const context = React.useContext(ChartContext)

  if (!context) {
    throw new Error("useChart must be used within a <ChartContainer />")
  }

  return context
}

function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig
  children: React.ComponentProps<
    typeof RechartsPrimitive.ResponsiveContainer
  >["children"]
}) {
  const uniqueId = React.useId()
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-slot="chart"
        data-chart={chartId}
        className={cn(
          "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-border/50 [&_.recharts-curve.recharts-tooltip-cursor]:stroke-border [&_.recharts-polar-grid_[stroke='#ccc']]:stroke-border [&_.recharts-radial-bar-background-sector]:fill-muted [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-muted [&_.recharts-reference-line_[stroke='#ccc']]:stroke-border flex aspect-video justify-center text-xs [&_.recharts-dot[stroke='#fff']]:stroke-transparent [&_.recharts-layer]:outline-hidden [&_.recharts-sector]:outline-hidden [&_.recharts-sector[stroke='#fff']]:stroke-transparent [&_.recharts-surface]:outline-hidden",
          className
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>
          {children}
        </RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  )
}

const ChartStyle = ({ id, config }: { id: string; config: ChartConfig }) => {
  const colorConfig = Object.entries(config).filter(
    ([, config]) => config.theme || config.color
  )

  if (!colorConfig.length) {
    return null
  }

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: Object.entries(THEMES)
          .map(
            ([theme, prefix]) => `
${prefix} [data-chart=${id}] {
${colorConfig
  .map(([key, itemConfig]) => {
    const color =
      itemConfig.theme?.[theme as keyof typeof itemConfig.theme] ||
      itemConfig.color
    return color ? `  --color-${key}: ${color};` : null
  })
  .join("\n")}
}
`
          )
          .join("\n"),
      }}
    />
  )
}

const ChartTooltip = RechartsPrimitive.Tooltip

type TooltipValueType = number | string | Array<number | string>
type TooltipNameType = string

type ChartTooltipContentProps = Omit<
  RechartsTooltipProps<TooltipValueType, TooltipNameType>,
  "content"
> &
  React.HTMLAttributes<HTMLDivElement> & {
    active?: boolean
    payload?: RechartsPayload<TooltipValueType, TooltipNameType>[]
    label?: string | number
    hideLabel?: boolean
    hideIndicator?: boolean
    indicator?: "line" | "dot" | "dashed"
    nameKey?: string
    labelKey?: string
  }

function ChartTooltipContent({
  active,
  payload,
  className,
  indicator = "dot",
  hideLabel = false,
  hideIndicator = false,
  label,
  labelFormatter,
  labelClassName,
  formatter,
  color,
  nameKey,
  labelKey,
  ...divProps
}: ChartTooltipContentProps) {
  const { config } = useChart()

  const items = (payload ?? []) as RechartsPayload<
    TooltipValueType,
    TooltipNameType
  >[]

  const tooltipLabel = React.useMemo(() => {
    if (hideLabel || items.length === 0) {
      return null
    }

    const [item] = items
    const key = `${labelKey || item?.dataKey || item?.name || "value"}`
    const itemConfig = getPayloadConfigFromPayload(config, item, key)
    const value =
      !labelKey && typeof label === "string"
        ? config[label as keyof typeof config]?.label || label
        : itemConfig?.label

    if (labelFormatter) {
      return (
        <div className={cn("font-medium", labelClassName)}>
          {labelFormatter(value, items)}
        </div>
      )
    }

    if (!value) {
      return null
    }

    return <div className={cn("font-medium", labelClassName)}>{value}</div>
  }, [
    label,
    labelFormatter,
    hideLabel,
    labelClassName,
    config,
    labelKey,
    items,
  ])

  if (!active || items.length === 0) {
    return null
  }

  const nestLabel = items.length === 1 && indicator !== "dot"

  return (
    <div
      className={cn(
        "border-border/50 bg-background grid min-w-[8rem] items-start gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs shadow-xl",
        className
      )}
      {...divProps}
    >
      {!nestLabel ? tooltipLabel : null}
      <div className="grid gap-1.5">
        {items.map((item, index) => {
          const key = `${nameKey || item.name || item.dataKey || "value"}`
          const itemConfig = getPayloadConfigFromPayload(config, item, key)
          const indicatorColor = color || item.payload?.fill || item.color
          const numericValue =
            typeof item.value === "number"
              ? item.value
              : typeof item.value === "string"
                ? Number(item.value)
                : undefined

          return (
            <div
              key={`${item.dataKey ?? item.name ?? index}`}
              className={cn(
                "[&>svg]:text-muted-foreground flex w-full flex-wrap items-stretch gap-2 [&>svg]:h-2.5 [&>svg]:w-2.5",
                indicator === "dot" && "items-center"
              )}
            >
              {formatter && item?.value !== undefined && item.name ? (
                formatter(item.value, item.name, item, index, items)
              ) : (
                <>
                  {itemConfig?.icon ? (
                    <itemConfig.icon />
                  ) : (
                    !hideIndicator && (
                      <div
                        className={cn(
                          "shrink-0 rounded-[2px] border-(--color-border) bg-(--color-bg)",
                          {
                            "h-2.5 w-2.5": indicator === "dot",
                            "w-1": indicator === "line",
                            "w-0 border-[1.5px] border-dashed bg-transparent":
                              indicator === "dashed",
                            "my-0.5": nestLabel && indicator === "dashed",
                          }
                        )}
                        style={
                          {
                            "--color-bg": indicatorColor,
                            "--color-border": indicatorColor,
                          } as React.CSSProperties
                        }
                      />
                    )
                  )}
                  <div
                    className={cn(
                      "flex flex-1 justify-between leading-none",
                      nestLabel ? "items-end" : "items-center"
                    )}
                  >
                    <div className="grid gap-1.5">
                      {nestLabel ? tooltipLabel : null}
                      <span className="text-muted-foreground">
                        {itemConfig?.label || item.name}
                      </span>
                    </div>
                      {numericValue !== undefined && !Number.isNaN(numericValue) && (
                      <span className="text-foreground font-mono font-medium tabular-nums">
                          {numericValue.toLocaleString()}
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const ChartLegend = RechartsPrimitive.Legend

interface ChartLegendContentProps
  extends React.HTMLAttributes<HTMLDivElement> {
  hideIcon?: boolean
  payload?: LegendPayload[]
  verticalAlign?: RechartsLegendProps["verticalAlign"]
  nameKey?: string
}

function ChartLegendContent({
  className,
  hideIcon = false,
  payload,
  verticalAlign = "bottom",
  nameKey,
  ...divProps
}: ChartLegendContentProps) {
  const { config } = useChart()

  if (!payload?.length) {
    return null
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-4",
        verticalAlign === "top" ? "pb-3" : "pt-3",
        className
      )}
      {...divProps}
    >
      {payload.map((item) => {
        const key = `${nameKey || item.dataKey || "value"}`
        const itemConfig = getPayloadConfigFromPayload(config, item, key)

        return (
          <div
            key={`${item.value}-${item.dataKey}`}
            className={cn(
              "[&>svg]:text-muted-foreground flex items-center gap-1.5 [&>svg]:h-3 [&>svg]:w-3"
            )}
          >
            {itemConfig?.icon && !hideIcon ? (
              <itemConfig.icon />
            ) : (
              <div
                className="h-2 w-2 shrink-0 rounded-[2px]"
                style={{
                  backgroundColor: item.color,
                }}
              />
            )}
            {itemConfig?.label}
          </div>
        )
      })}
    </div>
  )
}

// Helper to extract item config from a payload.
function getPayloadConfigFromPayload(
  config: ChartConfig,
  payload: unknown,
  key: string
) {
  if (typeof payload !== "object" || payload === null) {
    return undefined
  }

  const payloadPayload =
    "payload" in payload &&
    typeof payload.payload === "object" &&
    payload.payload !== null
      ? payload.payload
      : undefined

  let configLabelKey: string = key

  if (
    key in payload &&
    typeof payload[key as keyof typeof payload] === "string"
  ) {
    configLabelKey = payload[key as keyof typeof payload] as string
  } else if (
    payloadPayload &&
    key in payloadPayload &&
    typeof payloadPayload[key as keyof typeof payloadPayload] === "string"
  ) {
    configLabelKey = payloadPayload[
      key as keyof typeof payloadPayload
    ] as string
  }

  return configLabelKey in config
    ? config[configLabelKey]
    : config[key as keyof typeof config]
}

// ============================================
// Advanced Chart Utilities and Types
// ============================================

// Типы графиков
export type ChartType = "area" | "line" | "bar"

// Периоды времени
export type TimePeriod = "7d" | "30d" | "90d" | "1y" | "all"

// Метрики для отображения
export type ChartMetric = {
  id: string
  label: string
  color: string
  icon?: React.ComponentType<{ className?: string }>
  enabled: boolean
}

// Утилита для фильтрации данных по периоду
export function filterDataByPeriod<T extends { date: string }>(
  data: T[],
  period: TimePeriod
): T[] {
  if (period === "all") {
    return data
  }

  const today = new Date()
  const endDate = new Date(today)
  let daysToShow = 365

  switch (period) {
    case "7d":
      daysToShow = 7
      break
    case "30d":
      daysToShow = 30
      break
    case "90d":
      daysToShow = 90
      break
    case "1y":
      daysToShow = 365
      break
  }

  const startDate = new Date(endDate)
  startDate.setDate(startDate.getDate() - daysToShow)

  return data.filter((item) => {
    const itemDate = new Date(item.date)
    return itemDate >= startDate && itemDate <= endDate
  })
}

// Форматирование даты для оси X в зависимости от количества дней
export function formatChartDate(date: string | Date, totalDays: number): string {
  const d = typeof date === "string" ? new Date(date) : date

  if (totalDays <= 7) {
    return d.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric" })
  } else if (totalDays <= 30) {
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })
  } else if (totalDays <= 90) {
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })
  } else {
    return d.toLocaleDateString("ru-RU", { month: "short", year: "2-digit" })
  }
}

// Форматирование даты для tooltip
export function formatChartTooltipDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date
  return d.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  })
}

// Вычисление изменения в процентах между первым и последним значением
export function calculateMetricChange<T extends Record<string, unknown>>(
  data: T[],
  metricId: string
): { value: string; isPositive: boolean } | null {
  if (data.length < 2) return null

  const first = data[0][metricId] as number
  const last = data[data.length - 1][metricId] as number

  if (first === 0 || typeof first !== "number" || typeof last !== "number") {
    return null
  }

  const change = ((last - first) / first) * 100
  return {
    value: Math.abs(change).toFixed(1),
    isPositive: change >= 0,
  }
}

// Создание ChartConfig из массива метрик
export function createChartConfigFromMetrics(
  metrics: ChartMetric[]
): ChartConfig {
  const config: ChartConfig = {}
  metrics.forEach((metric) => {
    if (metric.enabled) {
      config[metric.id] = {
        label: metric.label,
        color: metric.color,
        icon: metric.icon,
      }
    }
  })
  return config
}

// Хук для управления метриками
export function useMetrics(initialMetrics: ChartMetric[]) {
  const [metrics, setMetrics] = React.useState<ChartMetric[]>(initialMetrics)

  const toggleMetric = React.useCallback((metricId: string) => {
    setMetrics((prev) =>
      prev.map((m) => (m.id === metricId ? { ...m, enabled: !m.enabled } : m))
    )
  }, [])

  const activeMetrics = React.useMemo(
    () => metrics.filter((m) => m.enabled),
    [metrics]
  )

  const chartConfig = React.useMemo(
    () => createChartConfigFromMetrics(metrics),
    [metrics]
  )

  return {
    metrics,
    setMetrics,
    toggleMetric,
    activeMetrics,
    chartConfig,
  }
}

// Хук для получения количества дней из периода
export function getDaysFromPeriod(period: TimePeriod, totalDays?: number): number {
  switch (period) {
    case "7d":
      return 7
    case "30d":
      return 30
    case "90d":
      return 90
    case "1y":
      return 365
    case "all":
      return totalDays ?? 365
    default:
      return 30
  }
}

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  ChartStyle,
}
