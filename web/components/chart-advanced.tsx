"use client"

import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Line,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts"
import {
  IconChartArea,
  IconChartLine,
  IconChartBar,
  IconTrendingUp,
  IconTrendingDown,
  IconUsers,
  IconTicket,
  IconBuildingSkyscraper,
  IconMessageCircle,
} from "@tabler/icons-react"

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Типы графиков
type ChartType = "area" | "line" | "bar"

// Периоды времени
type TimePeriod = "7d" | "30d" | "90d" | "1y" | "all"

// Метрики для отображения
type Metric = {
  id: string
  label: string
  color: string
  icon?: React.ComponentType<{ className?: string }>
  enabled: boolean
}

// Генерация тестовых данных по дням
function generateDailyData(days: number): Array<{
  date: string
  tickets: number
  users: number
  spaces: number
  feedbacks: number
  revenue: number
}> {
  const data: Array<{
    date: string
    tickets: number
    users: number
    spaces: number
    feedbacks: number
    revenue: number
  }> = []
  
  const today = new Date()
  const startDate = new Date(today)
  startDate.setDate(startDate.getDate() - days)

  for (let i = 0; i < days; i++) {
    const date = new Date(startDate)
    date.setDate(date.getDate() + i)
    
    // Генерируем реалистичные данные с трендами и случайными колебаниями
    const dayOfWeek = date.getDay()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
    const baseMultiplier = isWeekend ? 0.6 : 1
    
    // Добавляем тренд роста
    const trendFactor = 1 + (i / days) * 0.3
    
    // Случайные колебания
    const randomFactor = 0.7 + Math.random() * 0.6
    
    data.push({
      date: date.toISOString().split("T")[0],
      tickets: Math.round((30 + Math.random() * 40) * baseMultiplier * trendFactor * randomFactor),
      users: Math.round((50 + Math.random() * 30) * trendFactor * randomFactor),
      spaces: Math.round((20 + Math.random() * 15) * baseMultiplier * trendFactor * randomFactor),
      feedbacks: Math.round((10 + Math.random() * 20) * baseMultiplier * trendFactor * randomFactor),
      revenue: Math.round((5000 + Math.random() * 3000) * baseMultiplier * trendFactor * randomFactor),
    })
  }

  return data
}

const defaultMetrics: Metric[] = [
  {
    id: "tickets",
    label: "Заявки",
    color: "hsl(var(--primary))",
    icon: IconTicket,
    enabled: true,
  },
  {
    id: "users",
    label: "Пользователи",
    color: "hsl(217.2, 91.2%, 59.8%)",
    icon: IconUsers,
    enabled: true,
  },
  {
    id: "spaces",
    label: "Помещения",
    color: "hsl(142.1, 76.2%, 36.3%)",
    icon: IconBuildingSkyscraper,
    enabled: false,
  },
  {
    id: "feedbacks",
    label: "Отзывы",
    color: "hsl(280.4, 78.2%, 60.2%)",
    icon: IconMessageCircle,
    enabled: false,
  },
  {
    id: "revenue",
    label: "Доход",
    color: "hsl(38.7, 92%, 50%)",
    icon: IconTrendingUp,
    enabled: false,
  },
]

export function ChartAdvanced() {
  const [chartType, setChartType] = React.useState<ChartType>("area")
  const [timePeriod, setTimePeriod] = React.useState<TimePeriod>("30d")
  const [metrics, setMetrics] = React.useState<Metric[]>(defaultMetrics)
  const [allData, setAllData] = React.useState(generateDailyData(365))

  // Фильтрация данных по выбранному периоду
  const filteredData = React.useMemo(() => {
    const today = new Date()
    const endDate = new Date(today)
    let daysToShow = 365

    switch (timePeriod) {
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
      case "all":
        daysToShow = allData.length
        break
    }

    const startDate = new Date(endDate)
    startDate.setDate(startDate.getDate() - daysToShow)

    return allData.filter((item) => {
      const itemDate = new Date(item.date)
      return itemDate >= startDate && itemDate <= endDate
    })
  }, [timePeriod, allData])

  // Форматирование даты для оси X
  const formatDate = (date: string) => {
    const d = new Date(date)
    const days = filteredData.length

    if (days <= 7) {
      return d.toLocaleDateString("ru-RU", { weekday: "short", day: "numeric" })
    } else if (days <= 30) {
      return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })
    } else if (days <= 90) {
      return d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })
    } else {
      return d.toLocaleDateString("ru-RU", { month: "short", year: "2-digit" })
    }
  }

  // Конфигурация графика
  const chartConfig = React.useMemo(() => {
    const config: ChartConfig = {}
    metrics.forEach((metric) => {
      if (metric.enabled) {
        config[metric.id] = {
          label: metric.label,
          color: metric.color,
        }
      }
    })
    return config
  }, [metrics])

  // Переключение метрики
  const toggleMetric = (metricId: string) => {
    setMetrics((prev) =>
      prev.map((m) =>
        m.id === metricId ? { ...m, enabled: !m.enabled } : m
      )
    )
  }

  // Подсчет активных метрик
  const activeMetricsCount = metrics.filter((m) => m.enabled).length

  // Вычисление изменений для метрик
  const calculateChange = (metricId: string) => {
    if (filteredData.length < 2) return null
    const first = filteredData[0][metricId as keyof typeof filteredData[0]] as number
    const last = filteredData[filteredData.length - 1][metricId as keyof typeof filteredData[0]] as number
    if (first === 0) return null
    const change = ((last - first) / first) * 100
    return {
      value: Math.abs(change).toFixed(1),
      isPositive: change >= 0,
    }
  }

  // Рендер графика в зависимости от типа
  const renderChart = () => {
    const commonProps = {
      data: filteredData,
      margin: { top: 5, right: 10, left: 10, bottom: 0 },
    }

    switch (chartType) {
      case "area":
        return (
          <AreaChart {...commonProps}>
            <defs>
              {metrics
                .filter((m) => m.enabled)
                .map((metric, index) => (
                  <linearGradient
                    key={metric.id}
                    id={`fill${metric.id}`}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="5%"
                      stopColor={metric.color}
                      stopOpacity={0.8}
                    />
                    <stop
                      offset="95%"
                      stopColor={metric.color}
                      stopOpacity={0.1}
                    />
                  </linearGradient>
                ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={formatDate}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("ru-RU", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })
                  }}
                  indicator="dot"
                />
              }
            />
            <YAxis tickLine={false} axisLine={false} />
            {metrics
              .filter((m) => m.enabled)
              .map((metric) => (
                <Area
                  key={metric.id}
                  type="monotone"
                  dataKey={metric.id}
                  stackId={activeMetricsCount > 1 ? "a" : undefined}
                  stroke={metric.color}
                  fill={`url(#fill${metric.id})`}
                  strokeWidth={2}
                />
              ))}
          </AreaChart>
        )

      case "line":
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={formatDate}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("ru-RU", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })
                  }}
                  indicator="dot"
                />
              }
            />
            <YAxis tickLine={false} axisLine={false} />
            {metrics
              .filter((m) => m.enabled)
              .map((metric) => (
                <Line
                  key={metric.id}
                  type="monotone"
                  dataKey={metric.id}
                  stroke={metric.color}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
          </LineChart>
        )

      case "bar":
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={formatDate}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("ru-RU", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })
                  }}
                  indicator="dot"
                />
              }
            />
            <YAxis tickLine={false} axisLine={false} />
            {metrics
              .filter((m) => m.enabled)
              .map((metric, index) => (
                <Bar
                  key={metric.id}
                  dataKey={metric.id}
                  fill={metric.color}
                  radius={[4, 4, 0, 0]}
                />
              ))}
          </BarChart>
        )
    }
  }

  return (
    <>
    <Card className="@container/card">
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <CardTitle className="text-lg font-semibold">
              Аналитика по дням
            </CardTitle>
            <CardDescription className="text-sm">
              Статистика за выбранный период
            </CardDescription>
          </div>
          <CardAction>
            <div className="flex flex-wrap items-center gap-2">
              {/* Переключатель типа графика */}
              <ToggleGroup
                type="single"
                value={chartType}
                onValueChange={(value) => value && setChartType(value as ChartType)}
                variant="outline"
                className="hidden sm:flex"
              >
                <ToggleGroupItem value="area" aria-label="Area chart" size="lg">
                  <IconChartArea className="h-4 w-4" />
                </ToggleGroupItem>
                <ToggleGroupItem value="line" aria-label="Line chart" size="lg">
                  <IconChartLine className="h-4 w-4" />
                </ToggleGroupItem>
                <ToggleGroupItem value="bar" aria-label="Bar chart" size="lg">
                  <IconChartBar className="h-4 w-4" />
                </ToggleGroupItem>
              </ToggleGroup>

              {/* Мобильная версия переключателя */}
              <Select value={chartType} onValueChange={(value) => setChartType(value as ChartType)}>
                <SelectTrigger className="w-[120px] sm:hidden h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="area">Область</SelectItem>
                  <SelectItem value="line">Линия</SelectItem>
                  <SelectItem value="bar">Столбцы</SelectItem>
                </SelectContent>
              </Select>

              {/* Выбор периода */}
              <ToggleGroup
                type="single"
                value={timePeriod}
                onValueChange={(value) => value && setTimePeriod(value as TimePeriod)}
                variant="outline"
                className="hidden sm:flex"
              >
                <ToggleGroupItem value="7d" size="lg">7д</ToggleGroupItem>
                <ToggleGroupItem value="30d" size="lg">30д</ToggleGroupItem>
                <ToggleGroupItem value="90d" size="lg">90д</ToggleGroupItem>
                <ToggleGroupItem value="1y" size="lg">1г</ToggleGroupItem>
                <ToggleGroupItem value="all" size="lg">Все</ToggleGroupItem>
              </ToggleGroup>

              <Select
                value={timePeriod}
                onValueChange={(value) => setTimePeriod(value as TimePeriod)}
              >
                <SelectTrigger className="w-[100px] sm:hidden h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">7 дней</SelectItem>
                  <SelectItem value="30d">30 дней</SelectItem>
                  <SelectItem value="90d">90 дней</SelectItem>
                  <SelectItem value="1y">1 год</SelectItem>
                  <SelectItem value="all">Все</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardAction>
        </div>
      </CardHeader>

      <CardContent className="px-2 pt-2 sm:px-6 sm:pt-4">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[350px] w-full sm:h-[450px]"
        >
          {renderChart()}
        </ChartContainer>

        {/* Выбор метрик - перемещено вниз */}
        

        {/* Статистика по метрикам */}
    
      </CardContent>
    </Card>
    <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t">
          {metrics.map((metric) => {
            const Icon = metric.icon
            return (
              <Button
                key={metric.id}
                variant={metric.enabled ? "default" : "outline"}
                size="sm"
                onClick={() => toggleMetric(metric.id)}
                className={cn(
                  "h-7 gap-1.5 text-xs",
                  metric.enabled && "shadow-sm"
                )}
              >
                {Icon && <Icon className="h-3 w-3" />}
                <span>{metric.label}</span>
              </Button>
            )
          })}
        </div>
    {activeMetricsCount > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {metrics
            .filter((m) => m.enabled)
            .map((metric) => {
              const Icon = metric.icon
              const lastValue = filteredData[filteredData.length - 1]?.[metric.id as keyof typeof filteredData[0]] as number
              const change = calculateChange(metric.id)

              return (
                <div
                  key={metric.id}
                  className="rounded-lg border bg-card p-6"
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    {Icon && (
                      <div style={{ color: metric.color }}>
                        <Icon className="h-4 w-4" />
                      </div>
                    )}
                    <span className="text-[10px] font-medium text-muted-foreground">
                      {metric.label}
                    </span>
                  </div>
                  <div className="text-xl font-bold">{lastValue?.toLocaleString() || 0}</div>
                  {change && (
                    <div
                      className={cn(
                        "flex items-center gap-1 text-[10px] mt-0.5",
                        change.isPositive
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      )}
                    >
                      {change.isPositive ? (
                        <IconTrendingUp className="h-2.5 w-2.5" />
                      ) : (
                        <IconTrendingDown className="h-2.5 w-2.5" />
                      )}
                      <span>{change.value}%</span>
                    </div>
                  )}
                </div>
              )
            })}
        </div>
      )}
    </>
  )
}
