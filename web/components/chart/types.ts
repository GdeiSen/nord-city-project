/**
 * Chart configuration types for the configurable dashboard chart component.
 * Mirrors the structure of data-table types for consistency.
 */

export type ChartPeriod = "week" | "month" | "year"

export type ChartEntity =
  | "service_tickets"
  | "users"
  | "feedbacks"
  | "rental_spaces"
  | "rental_objects"

export type ChartMetric = "count" | "size"

export type ChartAggregation = "sum" | "avg" | "count"

export interface ChartConfig {
  period: ChartPeriod
  /** Reference date (ISO string) for data range — used with arrows to navigate */
  anchorDate: string
  entity: ChartEntity
  metric: ChartMetric
  aggregation: ChartAggregation
}

export const CHART_PERIOD_LABELS: Record<ChartPeriod, string> = {
  week: "Неделя",
  month: "Месяц",
  year: "Год",
}

export const CHART_ENTITY_LABELS: Record<ChartEntity, string> = {
  service_tickets: "Заявки на обслуживание",
  users: "Пользователи",
  feedbacks: "Отзывы",
  rental_spaces: "Помещения",
  rental_objects: "Бизнес-центры",
}

export const CHART_METRIC_LABELS: Record<ChartMetric, string> = {
  count: "Количество",
  size: "Площадь, м²",
}

export const CHART_AGGREGATION_LABELS: Record<ChartAggregation, string> = {
  sum: "Сумма",
  avg: "Среднее",
  count: "Количество",
}

/** Data point for chart rendering */
export interface ChartDataPoint {
  label: string
  value: number
  date: string
}
