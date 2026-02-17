"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { RentalSpace } from "@/types"
import { rentalSpaceApi, rentalObjectApi } from "@/lib/api"
import { MediaUploader } from "@/components/media-uploader"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useLoading, useSpaceRouteIds } from "@/hooks"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

const DEFAULT_STATUS = "FREE"

export default function SpaceEditPage() {
  const router = useRouter()
  const { objectId, spaceId, isEdit } = useSpaceRouteIds()

  const { loading, withLoading } = useLoading(true)
  const [objectName, setObjectName] = useState<string>("")
  const [formData, setFormData] = useState<Partial<RentalSpace>>({
    object_id: objectId ?? undefined,
    status: DEFAULT_STATUS,
    photos: [],
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (objectId == null || Number.isNaN(objectId)) return
    const load = async () => {
      const obj = await rentalObjectApi.getById(objectId)
      setObjectName(obj?.name ?? "")
      if (isEdit) {
        const spaceData = await rentalSpaceApi.getById(spaceId!)
        setFormData({
          ...spaceData,
          photos: spaceData.photos ?? [],
        })
      } else {
        setFormData({
          object_id: objectId,
          status: DEFAULT_STATUS,
          photos: [],
          floor: "",
          size: undefined,
          description: "",
        })
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      router.push(`/spaces/${objectId}`)
    })
  }, [objectId, spaceId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === "size" ? (value ? Number(value) : undefined) : value,
    }))
  }

  const handleStatusChange = (value: string) => {
    setFormData((prev) => ({ ...prev, status: value }))
  }

  const handlePhotosChange = (links: string[]) => {
    setFormData((prev) => ({ ...prev, photos: links }))
  }

  const handleSave = async () => {
    if (!formData.floor?.trim()) {
      toast.error("Укажите этаж помещения")
      return
    }
    if (!formData.size || formData.size <= 0) {
      toast.error("Площадь должна быть больше нуля")
      return
    }

    setSaving(true)
    try {
      const payload: Record<string, unknown> = {
        object_id: objectId,
        floor: String(formData.floor ?? "").trim(),
        size: Math.round(Number(formData.size) * 10) / 10 || 0,
        status: formData.status ?? DEFAULT_STATUS,
        photos: (formData.photos ?? []).map((u) => String(u).trim()).filter(Boolean),
      }
      if (formData.description != null && formData.description !== "") {
        payload.description = formData.description
      }

      if (isEdit) {
        await rentalSpaceApi.update(spaceId!, payload)
        toast.success("Помещение обновлено")
        router.push(`/spaces/${objectId}/${spaceId}`)
      } else {
        const created = await rentalSpaceApi.create(payload)
        toast.success("Помещение создано")
        router.push(`/spaces/${objectId}/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit) return
    try {
      await rentalSpaceApi.delete(spaceId!)
      toast.success("Помещение удалено")
      router.push(`/spaces/${objectId}`)
    } catch (err: any) {
      toast.error("Не удалось удалить", { description: err?.message })
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
                <BreadcrumbPage>{isEdit ? `Редактирование помещения #${spaceId}` : "Новое помещение"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">{isEdit ? "Редактирование помещения" : "Новое помещение"}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение данных помещения." : "Добавьте новое помещение в бизнес-центр."}
              </p>
            </div>
            <div>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <div className="grid gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="floor">Этаж</Label>
                    <Input
                      id="floor"
                      name="floor"
                      placeholder="Например, 5 или 5-6"
                      value={formData.floor ?? ""}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="size">Площадь, м²</Label>
                    <Input
                      id="size"
                      name="size"
                      type="number"
                      min={0.1}
                      step="0.1"
                      value={formData.size ?? ""}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="status">Статус</Label>
                    <Select value={formData.status ?? DEFAULT_STATUS} onValueChange={handleStatusChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="FREE">Свободно</SelectItem>
                        <SelectItem value="RESERVED">Забронировано</SelectItem>
                        <SelectItem value="OCCUPIED">Сдано</SelectItem>
                        <SelectItem value="MAINTENANCE">На обслуживании</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="description">Описание</Label>
                    <Textarea
                      id="description"
                      name="description"
                      placeholder="Кратко опишите особенности помещения"
                      value={formData.description ?? ""}
                      onChange={handleInputChange}
                      rows={4}
                    />
                  </div>
                  <MediaUploader
                    label="Фото и видео"
                    description="Загрузите фотографии или короткие видео помещения."
                    value={formData.photos ?? []}
                    onChange={handlePhotosChange}
                  />

                  <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-4">
                    {isEdit && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="outline"
                            className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 sm:mr-auto"
                          >
                            Удалить
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Удалить это помещение?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Это действие нельзя отменить.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={handleDelete}
                            >
                              Удалить
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                    <Button onClick={handleSave} disabled={saving}>
                      {saving ? "Сохранение..." : "Сохранить"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
