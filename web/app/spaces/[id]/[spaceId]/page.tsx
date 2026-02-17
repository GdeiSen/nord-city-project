"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { MediaCarousel } from "@/components/media-carousel"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit } from "@tabler/icons-react"
import { RentalSpace } from "@/types"
import { rentalSpaceApi, rentalObjectApi } from "@/lib/api"
import { formatDate } from "@/lib/date-utils"
import { useLoading, useSpaceRouteIds } from "@/hooks"
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

const SPACE_STATUS_LABELS: Record<string, string> = {
  FREE: "Свободно",
  RESERVED: "Забронировано",
  OCCUPIED: "Сдано",
  MAINTENANCE: "На обслуживании",
}

const SPACE_STATUS_VARIANTS: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  FREE: "default",
  RESERVED: "secondary",
  OCCUPIED: "destructive",
  MAINTENANCE: "outline",
}

export default function SpaceDetailPage() {
  const router = useRouter()
  const { objectId, spaceId } = useSpaceRouteIds()
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [space, setSpace] = useState<RentalSpace | null>(null)
  const [objectName, setObjectName] = useState<string>("")

  useEffect(() => {
    if (!spaceId || Number.isNaN(spaceId) || !objectId || Number.isNaN(objectId)) return
    withLoading(async () => {
      const [spaceData, objectData] = await Promise.all([
        rentalSpaceApi.getById(spaceId),
        rentalObjectApi.getById(objectId),
      ])
      setSpace(spaceData)
      setObjectName(objectData?.name ?? "")
    }).catch((err: any) => {
      toast.error("Не удалось загрузить помещение", { description: err?.message })
      router.push(`/spaces/${objectId}`)
    })
  }, [spaceId, objectId])

  if (
    objectId == null ||
    spaceId == null ||
    Number.isNaN(objectId) ||
    Number.isNaN(spaceId)
  ) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
            <p className="text-lg font-medium">Помещение не найдено</p>
            <p className="text-sm text-muted-foreground">Некорректный идентификатор.</p>
            <Link href="/spaces" className="text-sm text-primary hover:underline">
              К списку
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
                    <Link href="/spaces">Бизнес-центры</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbLink asChild>
                    <Link href={`/spaces/${objectId}`}>{objectName || `#${objectId}`}</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>Помещение #{spaceId}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            {canEdit && (
              <Button asChild size="default" className="shrink-0">
                <Link href={`/spaces/${objectId}/edit/${spaceId}`} className="gap-2">
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
          ) : space ? (
            <div className="space-y-6">
              <div>
                <div className="flex flex-wrap items-center gap-4 mb-4">
                  <h1 className="text-2xl font-semibold">Помещение #{space.id}</h1>
                  <Badge variant={SPACE_STATUS_VARIANTS[space.status] ?? "secondary"} className="text-sm px-3 py-1">
                    {SPACE_STATUS_LABELS[space.status] ?? space.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  Создано {formatDate(space.updated_at, { includeTime: true })}
                </p>
              </div>
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Этаж</div>
                    <p className="text-sm">{space.floor || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Площадь, м²</div>
                    <p className="text-sm font-medium">{space.size?.toLocaleString("ru-RU") ?? "—"}</p>
                  </div>
                </div>
                {space.description && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Описание</div>
                    <p className="text-sm whitespace-pre-wrap">{space.description}</p>
                  </div>
                )}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Фотографии</div>
                  <MediaCarousel items={space.photos ?? []} />
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
