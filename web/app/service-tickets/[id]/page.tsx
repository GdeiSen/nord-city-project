"use client"

import { useState, useEffect, useMemo } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit, IconLayoutSidebarRightCollapse, IconLayoutSidebarRightExpand } from "@tabler/icons-react"
import {
  ServiceTicket,
  AuditLogEntry,
  Feedback,
  TICKET_STATUS,
  TICKET_STATUS_LABELS_RU,
} from "@/types"
import { formatDate } from "@/lib/date-utils"
import { serviceTicketApi, userApi, rentalObjectApi, auditLogApi, feedbackApi } from "@/lib/api"
import { useLoading, useRouteId } from "@/hooks"
import { useCanEdit } from "@/hooks"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

const badgeClass = "text-sm px-3 py-1 h-7 min-h-7 items-center [&>svg]:size-4"

function getStatusBadge(status: string) {
  const label = getStatusLabel(status)
  const colorClass =
    status === TICKET_STATUS.NEW
      ? "bg-blue-500 text-white border-blue-500 hover:bg-blue-500"
      : status === TICKET_STATUS.ASSIGNED
        ? "bg-gray-500 text-white border-gray-500 hover:bg-gray-500"
        : status === TICKET_STATUS.IN_PROGRESS || status === TICKET_STATUS.ACCEPTED
          ? "bg-orange-500 text-white border-orange-500 hover:bg-orange-500"
          : status === TICKET_STATUS.COMPLETED
            ? "bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-600"
            : ""
  return <Badge variant="outline" className={`${badgeClass} ${colorClass}`.trim()}>{label}</Badge>
}

function getAssigneeDisplay(users: any[], entry: AuditLogEntry, status?: string | null): string {
  if (entry.actor?.label) return entry.actor.label
  if (entry.actor_display) return entry.actor_display
  const meta = entry.meta as Record<string, unknown> | undefined
  const assigneeName = meta?.assignee as string | undefined
  if (assigneeName) return assigneeName
  const assigneeId = meta?.assignee_id as number | undefined
  if (status === TICKET_STATUS.ASSIGNED && assigneeId != null && assigneeId > 0) {
    const u = users.find((x) => x.id === assigneeId)
    return u ? [u.last_name, u.first_name].filter(Boolean).join(" ") || (u.username ? `@${u.username}` : `#${assigneeId}`) : `#${assigneeId}`
  }
  const aid = entry.actor_id
  if (aid == null || aid === 0 || aid === 1) return "Система"
  const u = users.find((x) => x.id === aid)
  return u ? [u.last_name, u.first_name].filter(Boolean).join(" ") || (u.username ? `@${u.username}` : `#${aid}`) : `#${aid}`
}

function getStatusLabel(status: string): string {
  return TICKET_STATUS_LABELS_RU[status as keyof typeof TICKET_STATUS_LABELS_RU] || status || "—"
}

/** Extract status from new_data; handles smart diff format {old, new} */
function getStatusFromEntry(entry: AuditLogEntry): string | null {
  if (entry.action === "delete") return null
  const status = (entry.new_data as any)?.status
  if (status == null) return null
  if (typeof status === "object" && "new" in status) return status.new
  return typeof status === "string" ? status : null
}

function getAuditDotClass(entry: AuditLogEntry): string {
  const status = getStatusFromEntry(entry)
  if (entry.action === "create") {
    return "bg-blue-500"
  }
  if (status === TICKET_STATUS.NEW) {
    return "bg-blue-500"
  }
  if (status === TICKET_STATUS.ASSIGNED) {
    return "bg-slate-500"
  }
  if (status === TICKET_STATUS.IN_PROGRESS || status === TICKET_STATUS.ACCEPTED) {
    return "bg-orange-500"
  }
  if (status === TICKET_STATUS.COMPLETED) {
    return "bg-emerald-500"
  }
  if ((entry.event_type || "").toUpperCase() === "STATE_CHANGE") {
    return "bg-amber-500"
  }
  return "bg-zinc-400"
}

function getTransferTargetDisplay(users: any[], entry: AuditLogEntry): string | null {
  const meta = entry.meta as Record<string, unknown> | undefined
  const assigneeDisplay = meta?.assignee_display as string | undefined
  if (assigneeDisplay && assigneeDisplay.trim()) {
    return assigneeDisplay.trim()
  }
  const assigneeName = meta?.assignee as string | undefined
  if (assigneeName && assigneeName.trim()) {
    return assigneeName.trim()
  }
  const assigneeId = meta?.assignee_id as number | undefined
  if (assigneeId != null && assigneeId > 0) {
    const user = users.find((item) => item.id === assigneeId)
    if (user) {
      return [user.last_name, user.first_name].filter(Boolean).join(" ")
        || (user.username ? `@${user.username}` : `#${assigneeId}`)
    }
    return `#${assigneeId}`
  }
  return null
}

function getStatusTimelineLabel(entry: AuditLogEntry, users: any[]): string | null {
  const actor = getAssigneeDisplay(users, entry, getStatusFromEntry(entry))
  if (entry.action === "create") {
    return `Создана · ${actor}`
  }

  const status = getStatusFromEntry(entry)
  if (status === TICKET_STATUS.ACCEPTED || status === TICKET_STATUS.IN_PROGRESS) {
    return `Принята · ${actor}`
  }
  if (status === TICKET_STATUS.ASSIGNED) {
    const target = getTransferTargetDisplay(users, entry)
    return target ? `Передана · ${actor} -> ${target}` : `Передана · ${actor}`
  }
  if (status === TICKET_STATUS.COMPLETED) {
    return `Выполнена · ${actor}`
  }
  return null
}

function isStatusTimelineEntry(entry: AuditLogEntry): boolean {
  if (entry.action === "create") {
    return true
  }
  const status = getStatusFromEntry(entry)
  return [
    TICKET_STATUS.ACCEPTED,
    TICKET_STATUS.IN_PROGRESS,
    TICKET_STATUS.ASSIGNED,
    TICKET_STATUS.COMPLETED,
  ].includes(status as any)
}

function isImageUrl(url: string): boolean {
  return /\.(jpe?g|png|gif|webp|svg)(\?|$)/i.test(url)
}

function getAttachmentName(url: string): string {
  const tail = url.split("/").pop() || "file"
  const clean = tail.split("?")[0]
  const parts = clean.split("_")
  return parts.length > 1 ? parts.slice(1).join("_") : clean
}

export default function ServiceTicketDetailPage() {
  const router = useRouter()
  const { id: ticketId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [ticket, setTicket] = useState<ServiceTicket | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([])
  const [users, setUsers] = useState<any[]>([])
  const [isAuditPanelOpen, setIsAuditPanelOpen] = useState(true)

  useEffect(() => {
    if (!ticketId || Number.isNaN(ticketId)) return
    withLoading(async () => {
      const [ticketData, usersList, feedbackData] = await Promise.all([
        serviceTicketApi.getById(Number(ticketId)),
        userApi.getAll(),
        feedbackApi.getByServiceTicket(Number(ticketId)).catch(() => null),
      ])
      setUsers(usersList)
      setFeedback(feedbackData)
      try {
        const logs = await auditLogApi.getByEntity("ServiceTicket", Number(ticketId))
        setAuditLogs(Array.isArray(logs) ? logs : [])
      } catch {
        setAuditLogs([])
      }
      const user = usersList.find((u) => u.id === ticketData.user_id)
      const objectId = ticketData.object_id ?? (user as any)?.object_id
      let object: { id: number; name: string } | undefined
      if (objectId) {
        try {
          const obj = await rentalObjectApi.getById(objectId)
          object = { id: obj.id, name: obj.name ?? obj.address ?? `БЦ-${obj.id}` }
        } catch {
          object = { id: objectId, name: `БЦ-${objectId}` }
        }
      }
      setTicket({
        ...ticketData,
        user: user || ({ first_name: "Unknown", last_name: "", username: "" } as any),
        object,
      })
    }).catch((err: any) => {
      toast.error("Не удалось загрузить заявку", { description: err?.message })
      router.push("/service-tickets")
    })
  }, [ticketId, router, withLoading])

  const statusTimelineEntries = useMemo(
    () => auditLogs.filter(isStatusTimelineEntry),
    [auditLogs]
  )

  if (ticketId == null || (typeof ticketId === "number" && Number.isNaN(ticketId))) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
            <p className="text-lg font-medium">Заявка не найдена</p>
            <p className="text-sm text-muted-foreground">Некорректный идентификатор заявки.</p>
            <Link href="/service-tickets" className="text-sm text-primary hover:underline">
              К списку заявок
            </Link>
          </div>
        </SidebarInset>
        <Toaster />
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset className="flex flex-col min-h-0">
        <SiteHeader />
        <div className="flex-1 min-w-0 flex flex-col lg:flex-row min-h-0">
          {/* Левая часть: весь контент заявки с прокруткой */}
          <div className="flex-1 min-w-0 overflow-y-auto flex flex-col gap-4 p-4 md:p-8 pt-6 lg:pr-6">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <BreadcrumbLink asChild>
                      <Link href="/service-tickets">Заявки</Link>
                    </BreadcrumbLink>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                  <BreadcrumbPage>#{ticketId}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
              <div className="flex flex-wrap items-center gap-2">
                {canEdit && (
                  <Button asChild size="default" className="shrink-0">
                    <Link href={`/service-tickets/edit/${ticketId}`} className="gap-2">
                      <IconEdit className="h-4 w-4" />
                      Редактировать
                    </Link>
                  </Button>
                )}
                {ticket && (
                  <Button
                    type="button"
                    variant="outline"
                    size="default"
                    className="h-9 w-9 shrink-0 px-0"
                    aria-label={isAuditPanelOpen ? "Скрыть журнал" : "Показать журнал"}
                    title={isAuditPanelOpen ? "Скрыть журнал" : "Показать журнал"}
                    onClick={() => setIsAuditPanelOpen((current) => !current)}
                  >
                    {isAuditPanelOpen ? (
                      <IconLayoutSidebarRightCollapse className="h-4 w-4" />
                    ) : (
                      <IconLayoutSidebarRightExpand className="h-4 w-4" />
                    )}
                  </Button>
                )}
              </div>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : ticket ? (
              <div className="space-y-6">
                <div>
                  <div className="flex flex-wrap items-center gap-4 mb-4">
                    <h1 className="text-2xl font-semibold">Заявка #{ticket.id}</h1>
                    {getStatusBadge(ticket.status)}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Создана {formatDate(ticket.created_at)}
                    {ticket.updated_at !== ticket.created_at && (
                      <> · Обновлена {formatDate(ticket.updated_at)}</>
                    )}
                  </p>
                </div>
                <div className="space-y-6">
                  <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Описание</div>
                      <p className="text-sm">{ticket.description || "—"}</p>
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Местоположение</div>
                      <p className="text-sm">{ticket.location || "—"}</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Пользователь</div>
                    <p className="text-sm font-medium">
                      {ticket.user?.last_name} {ticket.user?.first_name}{" "}
                      {ticket.user?.username ? `(@${ticket.user.username})` : ""}
                    </p>
                    {ticket.user?.email && (
                      <p className="text-sm text-muted-foreground">{ticket.user.email}</p>
                    )}
                  </div>

                  {ticket.object && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Объект</div>
                      <Link
                        href={`/spaces/${ticket.object.id}`}
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        {ticket.object.name}
                      </Link>
                    </div>
                  )}

                  {ticket.answer && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Ответ</div>
                      <p className="text-sm">{ticket.answer}</p>
                    </div>
                  )}

                  <div className="space-y-3 rounded-lg border bg-muted/20 p-4">
                    <div>
                      <div>
                        <div className="text-sm font-medium">Отзыв по выполнению</div>
                        <p className="text-sm text-muted-foreground">
                          {feedback
                            ? `Оставлен ${formatDate(feedback.created_at, { includeTime: true })}`
                            : ticket.status === TICKET_STATUS.COMPLETED
                              ? "Клиент ещё не оставил отзыв по этой заявке."
                              : "Отзыв появится после завершения заявки и ответа клиента."}
                        </p>
                      </div>
                    </div>
                    {feedback ? (
                      <div className="space-y-3">
                        <div className="space-y-1">
                          <div className="text-xs text-muted-foreground">Ответ</div>
                          <p className="text-sm font-medium">{feedback.answer || "—"}</p>
                        </div>
                        {feedback.text && (
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">Комментарий</div>
                            <p className="text-sm whitespace-pre-wrap">{feedback.text}</p>
                          </div>
                        )}
                        <div>
                          <Link
                            href={`/feedbacks/${feedback.id}`}
                            className="text-sm font-medium text-primary hover:underline"
                          >
                            Открыть карточку отзыва
                          </Link>
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {ticket.attachment_urls && ticket.attachment_urls.length > 0 && (
                    <div className="space-y-3">
                      <div className="text-sm font-medium text-muted-foreground">Вложения</div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        {ticket.attachment_urls.map((url) => (
                          <a
                            key={url}
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="rounded-md border bg-muted/20 p-3 transition-colors hover:bg-muted/40"
                          >
                            {isImageUrl(url) ? (
                              <img src={url} alt="" className="mb-3 aspect-video w-full rounded object-cover" />
                            ) : null}
                            <div className="truncate text-sm font-medium">{getAttachmentName(url)}</div>
                            <div className="truncate text-xs text-muted-foreground">{url}</div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          {/* Правый aside: история изменений — встроен в layout, полная высота, на мобильных под контентом */}
          {ticket && isAuditPanelOpen && (
            <aside
              className={`
                order-2 lg:order-none mt-6 lg:mt-0
                w-full lg:w-80 lg:shrink-0
                min-h-[200px] lg:min-h-0
                bg-white lg:border-l border-border/50
              `}
            >
              <div
                className={`
                  min-h-[200px] min-w-0 overflow-y-auto
                  [&::-webkit-scrollbar]:w-1.5
                  [&::-webkit-scrollbar-track]:bg-transparent
                  [&::-webkit-scrollbar-thumb]:rounded-full
                  [&::-webkit-scrollbar-thumb]:bg-muted-foreground/25
                `}
                style={{ scrollbarWidth: "thin" }}
              >
                <div className="px-4 lg:px-5 pt-4 lg:pt-5 pb-4 lg:pb-5">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-muted-foreground">Статусы заявки</div>
                    <div className="text-xs text-muted-foreground">{statusTimelineEntries.length}</div>
                  </div>
                  {statusTimelineEntries.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Нет записей</p>
                  ) : (
                    <ul className="space-y-0.5 -mx-2">
                      {statusTimelineEntries.map((entry, i) => {
                        const label = getStatusTimelineLabel(entry, users) ?? entry.action
                        return (
                          <li
                            key={entry.id ?? `timeline-${i}`}
                            className="cursor-pointer rounded-sm px-2 py-1 hover:bg-muted/40"
                            title={`${label} · ${formatDate(entry.created_at as string, { includeTime: true })}`}
                            onClick={() => {
                              if (entry.id != null) {
                                router.push(`/audit-log?entryId=${entry.id}`)
                              }
                            }}
                            tabIndex={0}
                            onKeyDown={(event) => {
                              if ((event.key === "Enter" || event.key === " ") && entry.id != null) {
                                event.preventDefault()
                                router.push(`/audit-log?entryId=${entry.id}`)
                              }
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <span className={`h-2 w-2 shrink-0 rounded-full ${getAuditDotClass(entry)}`} />
                              <span className="block min-w-0 flex-1 truncate text-xs text-foreground">
                                {label}
                              </span>
                              <span className="shrink-0 text-[11px] text-muted-foreground">
                                {formatDate(entry.created_at as string, { includeTime: true })}
                              </span>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </div>
              </div>
            </aside>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
