"use client"

import Link from "next/link"
import type { ReactNode } from "react"

import type { AuditLogEntry } from "@/types"
import { formatDate } from "@/lib/date-utils"
import { Separator } from "@/components/ui/separator"
import { useIsMobile } from "@/hooks/ui/use-mobile"
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

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

export function getAuditEntityDetailUrl(entityType: string, entityId: number): string | null {
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
        className = match.endsWith(":")
          ? "text-sky-700 dark:text-sky-300"
          : "text-emerald-700 dark:text-emerald-300"
      } else if (match === "true" || match === "false") {
        className = "text-violet-700 dark:text-violet-300"
      } else if (match === "null") {
        className = "text-zinc-500 dark:text-zinc-400"
      } else {
        className = "text-amber-700 dark:text-amber-300"
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
    <div className="min-w-0 max-w-full space-y-2">
      <p className="text-sm font-medium">{title}</p>
      <div className="min-w-0 max-w-full overflow-hidden rounded-md border bg-muted/20">
        <div className="max-h-80 min-w-0 max-w-full overflow-x-auto overflow-y-auto">
          <div className="inline-block min-w-full align-top">
            <pre className="m-0 inline-block min-w-full p-3 text-xs leading-5 whitespace-pre">
              <code
                className="block"
                dangerouslySetInnerHTML={{
                  __html: getHighlightedJsonHtml(value),
                }}
              />
            </pre>
          </div>
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
    <div className="grid gap-0.5 sm:grid-cols-[9rem_minmax(0,1fr)] sm:gap-2">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="min-w-0 break-words text-sm">{value}</div>
    </div>
  )
}

function renderActor(entry: AuditLogEntry): ReactNode {
  const actor = entry.actor
  const label = actor?.label ?? entry.actor_display ?? entry.source_service ?? "Система"
  if (actor?.href) {
    return (
      <Link href={actor.href} className="text-primary hover:underline">
        {label}
      </Link>
    )
  }
  return <span>{label}</span>
}

function AuditEntryPanel({
  entry,
  detailUrl,
  emptyMessage = "Выберите запись в таблице, чтобы посмотреть детали.",
}: {
  entry: AuditLogEntry | null
  detailUrl: string | null
  emptyMessage?: string
}) {
  const oldStatus = getStatusValue(entry?.old_data)
  const newStatus = getStatusValue(entry?.new_data)

  return (
    <div className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden">
      {entry ? (
        <div className="min-w-0 max-w-full overflow-x-hidden space-y-4 p-4">
          <div className="space-y-2.5">
            <DetailRow
              label="Действие"
              value={entry.action}
            />
            <DetailRow label="Событие" value={entry.event_type} />
            <DetailRow
              label="Режим"
              value={
                MODE_LABELS[String(entry.audit_type || "").toLowerCase()] ??
                String(entry.audit_type || "—")
              }
            />
            {entry.retention_class ? (
              <DetailRow
                label="Хранение"
                value={RETENTION_LABELS[entry.retention_class] ?? entry.retention_class}
              />
            ) : null}
          </div>

          <Separator />

          <div className="space-y-2.5">
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
              value={renderActor(entry)}
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
          {emptyMessage}
        </div>
      )}
    </div>
  )
}

export function AuditEntryDetailsPanel({
  entry,
  emptyMessage,
}: {
  entry: AuditLogEntry | null
  emptyMessage?: string
}) {
  const detailUrl =
    entry != null ? getAuditEntityDetailUrl(entry.entity_type, entry.entity_id) : null
  return <AuditEntryPanel entry={entry} detailUrl={detailUrl} emptyMessage={emptyMessage} />
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
  const isMobile = useIsMobile()
  const detailUrl =
    entry != null ? getAuditEntityDetailUrl(entry.entity_type, entry.entity_id) : null

  const title = entry ? `Запись аудита #${entry.id}` : "Запись аудита"
  const description = entry
    ? `${entry.entity_type} #${entry.entity_id} · ${formatDate(entry.created_at, {
        includeTime: true,
      })}`
    : "Подробная информация о выбранной записи журнала."

  if (isMobile) {
    return (
      <Drawer open={open} onOpenChange={onOpenChange}>
        <DrawerContent className="max-h-[90vh] min-w-0 overflow-hidden">
          <DrawerHeader className="space-y-1 border-b pb-3">
            <DrawerTitle>{title}</DrawerTitle>
            <DrawerDescription>{description}</DrawerDescription>
          </DrawerHeader>
          <AuditEntryPanel entry={entry} detailUrl={detailUrl} />
        </DrawerContent>
      </Drawer>
    )
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-3/4 min-w-0 overflow-x-hidden flex-col gap-0 p-0 sm:max-w-xl"
      >
        <SheetHeader className="space-y-1 border-b pb-3">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        <AuditEntryPanel entry={entry} detailUrl={detailUrl} />
      </SheetContent>
    </Sheet>
  )
}
