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
import { rentalObjectApi } from "@/lib/api"
import { RentalObject } from "@/types"

export default function EditBusinessCenterPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const id = params?.id ? Number(params.id) : null

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<Partial<RentalObject>>({
    status: "ACTIVE",
    photos: [],
  })

  useEffect(() => {
    if (!id || Number.isNaN(id)) {
      setLoading(false)
      return
    }
    rentalObjectApi
      .getById(id)
      .then((data) => {
        setFormData({
          ...data,
          status: data.status ?? "ACTIVE",
          photos: [...(data.photos ?? [])],
        })
      })
      .catch((err) => {
        toast.error("Не удалось загрузить данные", { description: err?.message })
        router.push("/spaces")
      })
      .finally(() => setLoading(false))
  }, [id, router])

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleStatusChange = (value: string) => {
    setFormData((prev) => ({ ...prev, status: value }))
  }

  const handlePhotosChange = (links: string[]) => {
    setFormData((prev) => ({ ...prev, photos: links }))
  }

  const sanitizePayload = (data: Partial<RentalObject>): Partial<RentalObject> => {
    const { created_at, updated_at, spaces, users, id: _id, photos, ...rest } = data
    return {
      ...rest,
      status: rest.status ?? "ACTIVE",
      photos: (photos ?? []).map((url) => url.trim()).filter(Boolean),
    }
  }

  const handleSave = async () => {
    if (!id || Number.isNaN(id)) return
    const payload = sanitizePayload(formData)
    if (!payload.name?.trim()) {
      toast.error("Укажите название бизнес-центра")
      return
    }
    if (!payload.address?.trim()) {
      toast.error("Укажите адрес бизнес-центра")
      return
    }

    try {
      setSaving(true)
      await rentalObjectApi.update(id, payload)
      toast.success("Бизнес-центр обновлён")
    } catch (error: any) {
      toast.error("Не удалось сохранить", { description: error?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!id || !confirm(`Удалить бизнес-центр "${formData.name}"?`)) return
    try {
      await rentalObjectApi.delete(id)
      toast.success("Бизнес-центр удалён")
      router.push("/spaces")
    } catch (error: any) {
      toast.error("Не удалось удалить", { description: error?.message })
    }
  }

  const handleBack = () => router.push("/spaces")

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
            <h2 className="text-3xl font-bold tracking-tight">Редактирование бизнес-центра</h2>
            <Button variant="outline" onClick={handleBack}>
              <IconChevronLeft className="h-4 w-4 mr-2" />
              Назад
            </Button>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Основные данные</CardTitle>
              <CardDescription>Название, адрес и описание объекта</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Название</Label>
                <Input
                  id="name"
                  name="name"
                  placeholder="Например, БЦ Nord"
                  value={formData.name ?? ""}
                  onChange={handleInputChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="address">Адрес</Label>
                <Input
                  id="address"
                  name="address"
                  placeholder="Город, улица, дом"
                  value={formData.address ?? ""}
                  onChange={handleInputChange}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Описание</Label>
                <Textarea
                  id="description"
                  name="description"
                  placeholder="Краткое описание инфраструктуры"
                  value={formData.description ?? ""}
                  onChange={handleInputChange}
                  rows={4}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="status">Статус</Label>
                <Select value={formData.status ?? "ACTIVE"} onValueChange={handleStatusChange}>
                  <SelectTrigger id="status">
                    <SelectValue placeholder="Выберите статус" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ACTIVE">Активен</SelectItem>
                    <SelectItem value="INACTIVE">Неактивен</SelectItem>
                    <SelectItem value="ARCHIVED">Архив</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <PhotoLinksEditor
                label="Фотографии"
                description="Добавьте ссылки на изображения"
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
                <Button
                  variant="outline"
                  onClick={handleDelete}
                  className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600"
                >
                  Удалить
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
