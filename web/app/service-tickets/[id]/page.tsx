"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit } from "@tabler/icons-react"
import { ServiceTicket, AuditLogEntry, TICKET_STATUS, TICKET_STATUS_LABELS_RU } from "@/types"
import { formatDate } from "@/lib/date-utils"
import { serviceTicketApi, userApi, rentalObjectApi, auditLogApi } from "@/lib/api"
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
  const meta = entry.meta as Record<string, unknown> | undefined
  const assigneeName = meta?.assignee as string | undefined
  if (assigneeName) return assigneeName
  const assigneeId = meta?.assignee_id as number | undefined
  if (status === TICKET_STATUS.ASSIGNED && assigneeId != null && assigneeId > 0) {
    const u = users.find((x) => x.id === assigneeId)
    return u ? [u.last_name, u.first_name].filter(Boolean).join(" ") || u.username || `#${assigneeId}` : `#${assigneeId}`
  }
  const aid = entry.assignee_id
  if (aid == null || aid === 0 || aid === 1) return "Система"
  const u = users.find((x) => x.id === aid)
  return u ? [u.last_name, u.first_name].filter(Boolean).join(" ") || u.username || `#${aid}` : `#${aid}`
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

function getStatusBgClass(status: string | null): string {
  switch (status) {
    case TICKET_STATUS.NEW:
      return "bg-blue-500/10"
    case TICKET_STATUS.ASSIGNED:
      return "bg-gray-500/10"
    case TICKET_STATUS.IN_PROGRESS:
    case TICKET_STATUS.ACCEPTED:
      return "bg-orange-500/10"
    case TICKET_STATUS.COMPLETED:
      return "bg-emerald-500/10"
    default:
      return "bg-transparent"
  }
}

function getAuditLabel(entry: AuditLogEntry, users: any[]): string {
  const entryStatus = getStatusFromEntry(entry)
  const who = getAssigneeDisplay(users, entry, entryStatus)
  if (entry.action === "create") {
    return entryStatus ? `Создана · ${getStatusLabel(entryStatus)}` : "Создана"
  }
  if (entry.action === "delete") return "Удалена"
  if (entryStatus) return `${getStatusLabel(entryStatus)} · ${who}`
  return `Обновление · ${who}`
}

export default function ServiceTicketDetailPage() {
  const router = useRouter()
  const { id: ticketId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [ticket, setTicket] = useState<ServiceTicket | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([])
  const [users, setUsers] = useState<any[]>([])

  useEffect(() => {
    if (!ticketId || Number.isNaN(ticketId)) return
    withLoading(async () => {
      const [ticketData, usersList] = await Promise.all([
        serviceTicketApi.getById(Number(ticketId)),
        userApi.getAll(),
      ])
      setUsers(usersList)
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
  }, [ticketId])

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
              {canEdit && (
                <Button asChild size="default" className="shrink-0">
                  <Link href={`/service-tickets/edit/${ticketId}`} className="gap-2">
                    <IconEdit className="h-4 w-4" />
                    Редактировать
                  </Link>
                </Button>
              )}
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
                </div>
              </div>
            ) : null}
          </div>

          {/* Правый aside: история изменений — встроен в layout, полная высота, на мобильных под контентом */}
          {ticket && (
            <aside
              className={`
                order-2 lg:order-none mt-6 lg:mt-0
                w-full lg:w-72 lg:shrink-0
                min-h-[200px] lg:min-h-0
                bg-muted/60 lg:border-l border-border/50
                overflow-y-auto
                [&::-webkit-scrollbar]:w-1.5
                [&::-webkit-scrollbar-track]:bg-transparent
                [&::-webkit-scrollbar-thumb]:rounded-full
                [&::-webkit-scrollbar-thumb]:bg-muted-foreground/25
              `}
              style={{ scrollbarWidth: "thin" }}
            >
              <div className="px-4 lg:px-6 pt-4 lg:pt-6 pb-4 lg:pb-6">
                <div className="text-sm font-medium text-muted-foreground mb-4">История изменений</div>
                {auditLogs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Нет записей</p>
                ) : (
                  <ul className="space-y-1 -mx-4 lg:-mx-6">
                    {auditLogs.map((entry, i) => (
                      <li
                        key={entry.id ?? i}
                        className={`space-y-0.5 px-4 lg:px-6 py-2.5 ${getStatusBgClass(getStatusFromEntry(entry))}`}
                      >
                        <p className="text-sm font-medium">{getAuditLabel(entry, users)}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(entry.created_at as string, { includeTime: true })}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </aside>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
