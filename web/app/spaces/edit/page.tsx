"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { IconChevronLeft } from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { PageHeader } from "@/components/page-header"
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

export default function CreateBusinessCenterPage() {
  const router = useRouter()
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<Partial<RentalObject>>({
    status: "ACTIVE",
    photos: [],
  })

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
      const created = await rentalObjectApi.create(
        payload as Omit<RentalObject, "id" | "created_at" | "updated_at">
      )
      toast.success("Бизнес-центр создан")
      router.push(`/spaces/edit/${created.id}`)
    } catch (error: any) {
      toast.error("Не удалось сохранить", { description: error?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleBack = () => router.push("/spaces")

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">
          <PageHeader
            title="Новый бизнес-центр"
            description="Заполните информацию о бизнес-центре"
          />
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
                  <IconChevronLeft className="h-4 w-4 mr-2" />
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
