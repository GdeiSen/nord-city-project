"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { IconEdit } from "@tabler/icons-react"
import { Badge } from "@/components/ui/badge"
import { GuestParkingRequest } from "@/types"
import { formatDate } from "@/lib/date-utils"
import { guestParkingApi } from "@/lib/api"
import { useLoading, useRouteId, useCanEdit } from "@/hooks"
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

function formatArrivalInterval(request: GuestParkingRequest): string {
  const start = request.arrival_start_at || request.arrival_date
  const end = request.arrival_end_at
  if (!start) return "—"
  const date = formatDate(start, { includeTime: false })
  const startTime = formatDate(start, { includeTime: true }).split(" ").pop() || ""
  const endTime = end ? (formatDate(end, { includeTime: true }).split(" ").pop() || "") : ""
  return endTime ? `${date} ${startTime} - ${endTime}` : `${date} ${startTime}`
}

function statusBadge(status: GuestParkingRequest["status"]) {
  const label = status === "APPROVED" ? "Подтверждена" : status === "REJECTED" ? "Отклонена" : "Ожидает подтверждения"
  const colorClass = status === "APPROVED"
    ? "border-emerald-500 text-emerald-700"
    : status === "REJECTED"
      ? "border-red-500 text-red-700"
      : "border-amber-500 text-amber-700"
  return <Badge variant="outline" className={colorClass}>{label}</Badge>
}

export default function GuestParkingDetailPage() {
  const router = useRouter()
  const { id: reqId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [request, setRequest] = useState<GuestParkingRequest | null>(null)
  const [reviewing, setReviewing] = useState(false)

  useEffect(() => {
    if (!reqId || Number.isNaN(reqId)) return
    withLoading(async () => {
      const data = await guestParkingApi.getById(Number(reqId))
      setRequest(data)
    }).catch((err: any) => {
      toast.error("Не удалось загрузить заявку", { description: err?.message })
      router.push("/guest-parking")
    })
  }, [reqId])

  const reload = async () => {
    if (!reqId) return
    const data = await guestParkingApi.getById(Number(reqId))
    setRequest(data)
  }

  const handleApprove = async () => {
    if (!reqId) return
    setReviewing(true)
    try {
      await guestParkingApi.approve(Number(reqId))
      toast.success("Заявка подтверждена")
      await reload()
    } catch (err: any) {
      toast.error("Не удалось подтвердить заявку", { description: err?.message })
    } finally {
      setReviewing(false)
    }
  }

  const handleReject = async () => {
    if (!reqId) return
    const reason = window.prompt("Причина отклонения")
    if (reason === null) return
    setReviewing(true)
    try {
      await guestParkingApi.reject(Number(reqId), reason.trim() || undefined)
      toast.success("Заявка отклонена")
      await reload()
    } catch (err: any) {
      toast.error("Не удалось отклонить заявку", { description: err?.message })
    } finally {
      setReviewing(false)
    }
  }

  if (reqId == null || (typeof reqId === "number" && Number.isNaN(reqId))) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
            <p className="text-lg font-medium">Заявка не найдена</p>
            <Link href="/guest-parking" className="text-sm text-primary hover:underline">
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
                    <Link href="/guest-parking">Гостевая парковка</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>#{reqId}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            {canEdit && (
              <div className="flex flex-wrap items-center gap-2">
                {request?.status === "NEW" && (
                  <>
                    <Button type="button" variant="outline" onClick={handleReject} disabled={reviewing}>
                      Отклонить
                    </Button>
                    <Button type="button" onClick={handleApprove} disabled={reviewing}>
                      Подтвердить
                    </Button>
                  </>
                )}
                <Button asChild size="default" className="shrink-0">
                  <Link href={`/guest-parking/edit/${reqId}`} className="gap-2">
                    <IconEdit className="h-4 w-4" />
                    Редактировать
                  </Link>
                </Button>
              </div>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : request ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Заявка #{request.id}</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Создана {formatDate(request.created_at)}
                  {request.updated_at !== request.created_at && (
                    <> · Обновлена {formatDate(request.updated_at)}</>
                  )}
                </p>
                <div className="mt-3">{statusBadge(request.status || "NEW")}</div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Дата и интервал заезда</div>
                  <p className="text-sm">{formatArrivalInterval(request)}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Госномер</div>
                  <p className="text-sm font-medium">{request.license_plate}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Телефон арендатора</div>
                  <p className="text-sm">{request.tenant_phone || "—"}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Арендатор</div>
                  {request.user ? (
                    <Link
                      href={`/users/${request.user_id}`}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      {[request.user.last_name, request.user.first_name].filter(Boolean).join(" ")} {request.user.username ? `(@${request.user.username})` : ""}
                    </Link>
                  ) : (
                    <p className="text-sm">ID {request.user_id}</p>
                  )}
                </div>
                {request.status === "REJECTED" && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Причина отклонения</div>
                    <p className="text-sm">{request.rejection_reason || "—"}</p>
                  </div>
                )}
                {request.reviewed_at && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Рассмотрена</div>
                    <p className="text-sm">{formatDate(request.reviewed_at, { includeTime: true })}</p>
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
