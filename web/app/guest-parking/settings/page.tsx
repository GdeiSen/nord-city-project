"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"

import { AppSidebar } from "@/components/app-sidebar"
import { MediaUploader } from "@/components/media-uploader"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { SidebarInset } from "@/components/ui/sidebar"
import { useCanEdit } from "@/hooks"
import { guestParkingSettingsApi } from "@/lib/api"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

export default function GuestParkingSettingsPage() {
  const router = useRouter()
  const canEdit = useCanEdit()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [routeImages, setRouteImages] = useState<string[]>([])

  useEffect(() => {
    if (!canEdit) return

    let active = true
    guestParkingSettingsApi.get()
      .then((data) => {
        if (!active) return
        setRouteImages(Array.isArray(data?.route_images) ? data.route_images.slice(0, 2) : [])
      })
      .catch((err: any) => {
        toast.error("Не удалось загрузить настройки", { description: err?.message })
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [canEdit])

  const handleRouteImagesChange = (urls: string[]) => {
    if (urls.length > 2) {
      toast.error("Можно сохранить не более двух изображений")
    }
    setRouteImages(urls.slice(0, 2))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await guestParkingSettingsApi.update(routeImages.slice(0, 2))
      toast.success("Настройки сохранены")
      router.push("/guest-parking")
    } catch (err: any) {
      toast.error("Не удалось сохранить настройки", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link href="/guest-parking">Гостевая парковка</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Настройки</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          {!canEdit ? (
            <div className="text-sm text-destructive">Доступ только для администраторов.</div>
          ) : (
            <div className="max-w-2xl space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Настройки гостевой парковки</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Загрузите до двух изображений схемы проезда. Они будут показаны пользователю после подтверждения заявки.
                </p>
              </div>

              {loading ? (
                <div className="flex justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <div className="grid gap-6">
                  <MediaUploader
                    value={routeImages}
                    onChange={handleRouteImagesChange}
                    label="Изображения проезда"
                    description="Не более двух изображений. Файлы загружаются в media service."
                  />

                  <div className="flex justify-end pt-4">
                    <Button type="button" onClick={handleSave} disabled={saving}>
                      {saving ? "Сохранение..." : "Сохранить"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
