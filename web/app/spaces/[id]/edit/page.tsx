"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { IconChevronLeft } from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { PhotoLinksEditor } from "@/components/photo-links-editor"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { SidebarInset } from "@/components/ui/sidebar"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { rentalObjectApi, rentalSpaceApi } from "@/lib/api"
import { RentalObject, RentalSpace } from "@/types"

const SPACE_STATUS_LABELS: Record<string, string> = {
  FREE: "Свободно",
  RESERVED: "Забронировано",
  OCCUPIED: "Сдано",
  MAINTENANCE: "На обслуживании",
}

export default function CreateRentalSpacePage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const objectId = params?.id ? Number(params.id) : null

  const [loading, setLoading] = useState(true)
  const [rentalObject, setRentalObject] = useState<RentalObject | null>(null)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<Partial<RentalSpace>>({
    object_id: objectId ?? 0,
    status: "FREE",
    photos: [],
  })

  useEffect(() => {
    if (!objectId || Number.isNaN(objectId)) {
      setLoading(false)
      return
    }
    rentalObjectApi
      .getById(objectId)
      .then((data) => setRentalObject(data))
      .catch((err) => {
        toast.error("Не удалось загрузить объект", { description: err?.message })
        router.push(`/spaces/${objectId}`)
      })
      .finally(() => setLoading(false))
  }, [objectId, router])

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target
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

  const sanitizePayload = (data: Partial<RentalSpace>): Partial<RentalSpace> => {
    const { id: _id, object, views, created_at, updated_at, photos, ...rest } = data
    return {
      ...rest,
      object_id: objectId!,
      size: rest.size ? Number(rest.size) : undefined,
      status: rest.status ?? "FREE",
      photos: (photos ?? []).map((url) => url.trim()).filter(Boolean),
    }
  }

  const handleSave = async () => {
    if (!objectId || Number.isNaN(objectId)) return
    if (!formData.floor?.trim()) {
      toast.error("Укажите этаж помещения")
      return
    }
    if (!formData.size || Number(formData.size) <= 0) {
      toast.error("Площадь должна быть больше нуля")
      return
    }

    try {
      setSaving(true)
      const payload = sanitizePayload(formData)
      const created = await rentalSpaceApi.create(
        payload as Omit<RentalSpace, "id" | "created_at" | "updated_at">
      )
      toast.success("Помещение создано")
      router.push(`/spaces/${objectId}/edit/${created.id}`)
    } catch (error: any) {
      toast.error("Не удалось сохранить", { description: error?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleBack = () => router.push(`/spaces/${objectId}`)

  if (loading) {
    return (
      <>
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex-1 flex items-center justify-center p-8">
            <p className="text-muted-foreground">Загрузка...</p>
          </div>
        </SidebarInset>
      </>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">
          <div className="flex items-center justify-between">
            <h2 className="text-3xl font-bold tracking-tight">
              Новое помещение — {rentalObject?.name ?? "Объект"}
            </h2>
            <Button variant="outline" onClick={handleBack}>
              <IconChevronLeft className="h-4 w-4 mr-2" />
              Назад
            </Button>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Данные помещения</CardTitle>
              <CardDescription>Этаж, площадь и описание</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
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
                  min={1}
                  step="0.1"
                  value={formData.size ?? ""}
                  onChange={handleInputChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">Статус</Label>
                <Select value={formData.status ?? "FREE"} onValueChange={handleStatusChange}>
                  <SelectTrigger id="status">
                    <SelectValue placeholder="Выберите статус" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SPACE_STATUS_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>{label}</SelectItem>
                    ))}
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
              <PhotoLinksEditor
                label="Фотографии"
                description="Добавьте ссылки на фотографии помещения"
                value={formData.photos ?? []}
                onChange={handlePhotosChange}
                addButtonLabel="Добавить фото"
              />
              <div className="flex gap-2 pt-4">
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
                <Button variant="outline" onClick={handleBack}>
                  Назад
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
