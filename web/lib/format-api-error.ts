/**
 * Format API errors (e.g. from FastAPI) for display in toast/alert.
 */
export function formatApiError(err: unknown): { title: string; details: string } {
  const e = err as Error & { status?: number; details?: unknown }
  const title = e?.message || "Произошла ошибка"
  const parts: string[] = []

  if (e?.status) {
    parts.push(`Код ответа: ${e.status}`)
  }
  const details = e?.details
  if (Array.isArray(details)) {
    details.forEach((item: { loc?: string[]; msg?: string }) => {
      const loc = Array.isArray(item.loc) ? item.loc.join(" → ") : ""
      const msg = item.msg || ""
      if (msg) parts.push(loc ? `${loc}: ${msg}` : msg)
    })
  } else if (typeof details === "object" && details !== null) {
    const extra = (details as Record<string, string>).msg || JSON.stringify(details)
    if (extra && extra !== title) parts.push(extra)
  } else if (typeof details === "string" && details !== title) {
    parts.push(details)
  }

  return { title, details: parts.length ? parts.join("\n") : "" }
}
