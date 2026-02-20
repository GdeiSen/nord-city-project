"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { IconEdit } from "@tabler/icons-react"
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

export default function GuestParkingDetailPage() {
  const router = useRouter()
  const { id: reqId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [request, setRequest] = useState<GuestParkingRequest | null>(null)

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
              <Button asChild size="default" className="shrink-0">
                <Link href={`/guest-parking/edit/${reqId}`} className="gap-2">
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
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Дата и время заезда</div>
                  <p className="text-sm">{formatDate(request.arrival_date, { includeTime: true })}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Госномер</div>
                  <p className="text-sm font-medium">{request.license_plate}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Марка и цвет</div>
                  <p className="text-sm">{request.car_make_color}</p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Телефон водителя</div>
                  <p className="text-sm">{request.driver_phone}</p>
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
              </div>
            </div>
          ) : null}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
