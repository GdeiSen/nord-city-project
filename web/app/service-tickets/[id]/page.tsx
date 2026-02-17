"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit, IconClock, IconCheck, IconX, IconAlertTriangle } from "@tabler/icons-react"
import { ServiceTicket, TICKET_STATUS, TICKET_STATUS_LABELS_RU } from "@/types"
import { cn } from "@/lib/utils"
import { formatDate } from "@/lib/date-utils"
import { serviceTicketApi, userApi, rentalObjectApi } from "@/lib/api"
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
  switch (status) {
    case TICKET_STATUS.NEW:
      return <Badge variant="destructive" className={badgeClass}><IconX className="mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.NEW]}</Badge>
    case TICKET_STATUS.ACCEPTED:
      return <Badge variant="secondary" className={badgeClass}><IconClock className="mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ACCEPTED]}</Badge>
    case TICKET_STATUS.ASSIGNED:
      return <Badge variant="default" className={badgeClass}><IconAlertTriangle className="mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ASSIGNED]}</Badge>
    case TICKET_STATUS.COMPLETED:
      return <Badge variant="outline" className={badgeClass}><IconCheck className="mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.COMPLETED]}</Badge>
    default:
      return <Badge variant="outline" className={badgeClass}>Неизвестно</Badge>
  }
}

export default function ServiceTicketDetailPage() {
  const router = useRouter()
  const { id: ticketId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [ticket, setTicket] = useState<ServiceTicket | null>(null)

  useEffect(() => {
    if (!ticketId || Number.isNaN(ticketId)) return
    withLoading(async () => {
      const [ticketData, users] = await Promise.all([
        serviceTicketApi.getById(Number(ticketId)),
        userApi.getAll(),
      ])
      const user = users.find((u) => u.id === ticketData.user_id)
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
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
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
              <Button asChild size="sm">
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
      </SidebarInset>
      <Toaster />
    </>
  )
}
