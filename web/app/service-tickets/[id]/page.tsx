"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconChevronLeft, IconEdit, IconTicket, IconClock, IconCheck, IconX, IconAlertTriangle } from "@tabler/icons-react"
import { ServiceTicket, TICKET_STATUS, TICKET_STATUS_LABELS_RU, TICKET_PRIORITY, TICKET_PRIORITY_LABELS_RU } from "@/types"
import { serviceTicketApi, userApi } from "@/lib/api"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"
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

function getStatusBadge(status: string) {
  switch (status) {
    case TICKET_STATUS.NEW:
      return <Badge variant="destructive"><IconX className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.NEW]}</Badge>
    case TICKET_STATUS.ACCEPTED:
      return <Badge variant="secondary"><IconClock className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ACCEPTED]}</Badge>
    case TICKET_STATUS.ASSIGNED:
      return <Badge variant="default"><IconAlertTriangle className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ASSIGNED]}</Badge>
    case TICKET_STATUS.COMPLETED:
      return <Badge variant="outline"><IconCheck className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.COMPLETED]}</Badge>
    default:
      return <Badge variant="outline">Неизвестно</Badge>
  }
}

function getPriorityBadge(priority: number) {
  switch (priority) {
    case TICKET_PRIORITY.LOW:
      return <Badge variant="outline">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.LOW]}</Badge>
    case TICKET_PRIORITY.MEDIUM:
      return <Badge variant="secondary">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.MEDIUM]}</Badge>
    case TICKET_PRIORITY.HIGH:
      return <Badge variant="destructive">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.HIGH]}</Badge>
    case TICKET_PRIORITY.CRITICAL:
      return <Badge className="bg-red-600 hover:bg-red-700">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.CRITICAL]}</Badge>
    default:
      return <Badge variant="outline">Неопределен</Badge>
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function ServiceTicketDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const ticketId = Number(params?.id)
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [ticket, setTicket] = useState<ServiceTicket | null>(null)

  useEffect(() => {
    if (!ticketId || Number.isNaN(ticketId)) return
    withLoading(async () => {
      const [ticketData, users] = await Promise.all([
        serviceTicketApi.getById(ticketId),
        userApi.getAll(),
      ])
      const user = users.find((u) => u.id === ticketData.user_id)
      setTicket({
        ...ticketData,
        user: user || ({ first_name: "Unknown", last_name: "", username: "" } as any),
      })
    }).catch((err: any) => {
      toast.error("Не удалось загрузить заявку", { description: err?.message })
      router.push("/service-tickets")
    })
  }, [ticketId])

  if (Number.isNaN(ticketId)) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card>
          <CardHeader>
            <CardTitle>Заявка не найдена</CardTitle>
            <CardDescription>Некорректный идентификатор заявки.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => router.push("/service-tickets")}>
              К списку заявок
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
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

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/service-tickets" className="gap-2">
                <IconChevronLeft className="h-4 w-4" />
                Назад к списку
              </Link>
            </Button>
            {canEdit && (
              <Button asChild>
                <Link href={`/service-tickets/edit/${ticketId}`} className="gap-2">
                  <IconEdit className="h-4 w-4" />
                  Редактировать
                </Link>
              </Button>
            )}
          </div>

          {loading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </CardContent>
            </Card>
          ) : ticket ? (
            <div className="grid gap-6">
              <Card>
                <CardHeader className="space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <CardTitle className="flex items-center gap-2">
                      <IconTicket className="h-6 w-6" />
                      Заявка #{ticket.id}
                    </CardTitle>
                    <div className="flex flex-wrap gap-2">
                      {getStatusBadge(ticket.status)}
                      {getPriorityBadge(ticket.priority)}
                      {ticket.category && (
                        <Badge variant="outline">{ticket.category}</Badge>
                      )}
                    </div>
                  </div>
                  <CardDescription>
                    Создана {formatDate(ticket.created_at)}
                    {ticket.updated_at !== ticket.created_at && (
                      <> · Обновлена {formatDate(ticket.updated_at)}</>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
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

                  {ticket.answer && (
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Ответ</div>
                      <p className="text-sm">{ticket.answer}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : null}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
