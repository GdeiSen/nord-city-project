/**
 * Format date string for display.
 * @param dateString - ISO date string or parseable date
 * @param options - includeTime: true for detail pages (default), false for lists/cards; locale defaults to ru-RU
 */
export function formatDate(
  dateString: string,
  options?: { includeTime?: boolean; locale?: string }
): string {
  if (!dateString) return "—"
  const { includeTime = true, locale = "ru-RU" } = options ?? {}
  const opts: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  }
  if (includeTime) {
    opts.hour = "2-digit"
    opts.minute = "2-digit"
  }
  return new Date(dateString).toLocaleDateString(locale, opts)
}
