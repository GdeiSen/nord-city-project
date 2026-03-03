"use client"

import Link from "next/link"
import type { ReactNode } from "react"

import type { AuditLogEntry } from "@/types"
import { formatDate } from "@/lib/date-utils"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

const ACTION_LABELS: Record<string, string> = {
  create: "Создание",
  update: "Изменение",
  delete: "Удаление",
}

const MODE_LABELS: Record<string, string> = {
  fast: "Light",
  smart: "Smart",
  heavy: "Heavy",
}

const RETENTION_LABELS: Record<string, string> = {
  CRITICAL: "Critical",
  OPERATIONAL: "Operational",
  TECHNICAL: "Technical",
}

function getEntityDetailUrl(entityType: string, entityId: number): string | null {
  switch (entityType) {
    case "ServiceTicket":
      return `/service-tickets/${entityId}`
    case "GuestParkingRequest":
      return `/guest-parking/${entityId}`
    case "User":
      return `/users/${entityId}`
    case "Feedback":
      return `/feedbacks/${entityId}`
    case "Object":
      return `/spaces/${entityId}`
    case "Space":
      return `/spaces/${entityId}`
    default:
      return null
  }
}

function getStatusValue(data: Record<string, unknown> | undefined): string | null {
  if (!data || typeof data !== "object") return null
  const status = data.status
  if (typeof status !== "string" || !status.trim()) return null
  return status.trim()
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
}

function getHighlightedJsonHtml(value: Record<string, unknown>): string {
  const raw = escapeHtml(JSON.stringify(value, null, 2))

  return raw.replace(
    /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let className = "text-foreground"
      if (match.startsWith('"')) {
        className = match.endsWith(":") ? "text-sky-300" : "text-emerald-300"
      } else if (match === "true" || match === "false") {
        className = "text-violet-300"
      } else if (match === "null") {
        className = "text-muted-foreground"
      } else {
        className = "text-amber-300"
      }
      return `<span class="${className}">${match}</span>`
    }
  )
}

function JsonBlock({
  title,
  value,
}: {
  title: string
  value?: Record<string, unknown>
}) {
  if (!value || Object.keys(value).length === 0) return null

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{title}</p>
      <div className="overflow-hidden rounded-md border bg-muted/20">
        <div className="max-h-80 overflow-x-auto overflow-y-auto">
          <pre className="min-w-max p-3 text-xs leading-5 whitespace-pre">
            <code
              dangerouslySetInnerHTML={{
                __html: getHighlightedJsonHtml(value),
              }}
            />
          </pre>
        </div>
      </div>
    </div>
  )
}

function DetailRow({
  label,
  value,
}: {
  label: string
  value: ReactNode
}) {
  return (
    <div className="grid gap-1 sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="min-w-0 break-words text-sm">{value}</div>
    </div>
  )
}

export function AuditEntrySheet({
  entry,
  open,
  onOpenChange,
}: {
  entry: AuditLogEntry | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const detailUrl =
    entry != null ? getEntityDetailUrl(entry.entity_type, entry.entity_id) : null
  const oldStatus = getStatusValue(entry?.old_data)
  const newStatus = getStatusValue(entry?.new_data)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
        <SheetHeader className="space-y-2 border-b pb-4">
          <SheetTitle>
            {entry ? `Запись аудита #${entry.id}` : "Запись аудита"}
          </SheetTitle>
          <SheetDescription>
            {entry
              ? `${entry.entity_type} #${entry.entity_id} · ${formatDate(entry.created_at, { includeTime: true })}`
              : "Подробная информация о выбранной записи журнала."}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1">
          {entry ? (
            <div className="space-y-6 p-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant={entry.action === "delete" ? "destructive" : entry.action === "create" ? "default" : "secondary"}>
                  {ACTION_LABELS[entry.action] ?? entry.action}
                </Badge>
                <Badge variant="outline">{entry.event_type}</Badge>
                <Badge variant="outline">
                  {MODE_LABELS[String(entry.audit_type || "").toLowerCase()] ?? String(entry.audit_type || "—")}
                </Badge>
                {entry.retention_class ? (
                  <Badge variant="outline">
                    {RETENTION_LABELS[entry.retention_class] ?? entry.retention_class}
                  </Badge>
                ) : null}
              </div>

              <div className="space-y-4">
                <DetailRow
                  label="Сущность"
                  value={
                    detailUrl ? (
                      <Link href={detailUrl} className="text-primary hover:underline">
                        {entry.entity_type} #{entry.entity_id}
                      </Link>
                    ) : (
                      <span>
                        {entry.entity_type} #{entry.entity_id}
                      </span>
                    )
                  }
                />
                <DetailRow
                  label="Инициатор"
                  value={entry.actor_display ?? entry.source_service ?? "Система"}
                />
                <DetailRow
                  label="Тип инициатора"
                  value={entry.actor_type ?? "SYSTEM"}
                />
                <DetailRow
                  label="Источник"
                  value={entry.source_service ?? "—"}
                />
                <DetailRow
                  label="Создана"
                  value={formatDate(entry.created_at, { includeTime: true })}
                />
                {entry.reason ? <DetailRow label="Причина" value={entry.reason} /> : null}
                {entry.request_id ? <DetailRow label="Request ID" value={entry.request_id} /> : null}
                {entry.correlation_id ? (
                  <DetailRow label="Correlation ID" value={entry.correlation_id} />
                ) : null}
                {(oldStatus || newStatus) ? (
                  <DetailRow
                    label="Состояние"
                    value={
                      <span>
                        {oldStatus ?? "—"} {"→"} {newStatus ?? "—"}
                      </span>
                    }
                  />
                ) : null}
              </div>

              <Separator />

              <div className="space-y-4">
                <JsonBlock title="Предыдущее состояние" value={entry.old_data} />
                <JsonBlock title="Новое состояние" value={entry.new_data} />
                <JsonBlock title="Meta" value={entry.meta} />
              </div>
            </div>
          ) : (
            <div className="p-4 text-sm text-muted-foreground">
              Выберите запись в таблице, чтобы посмотреть детали.
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
