"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
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
import { RentalObject } from "@/types"
import { rentalObjectApi } from "@/lib/api"
import { PhotoLinksEditor } from "@/components/photo-links-editor"
import { useLoading } from "@/hooks/use-loading"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

export default function RentalObjectEditPage() {
  const params = useParams<{ id?: string[] }>()
  const router = useRouter()
  const idParam = params?.id?.[0]
  const objectId = idParam ? parseInt(idParam, 10) : null
  const isEdit = objectId != null && !Number.isNaN(objectId)

  const { loading, withLoading } = useLoading(true)
  const [formData, setFormData] = useState<Partial<RentalObject>>({ status: "ACTIVE", photos: [] })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!isEdit) {
      setFormData({ status: "ACTIVE", photos: [] })
      return
    }
    withLoading(async () => {
      const data = await rentalObjectApi.getById(objectId!)
      setFormData({ ...data, photos: data.photos ?? [] })
    }).catch((err: any) => {
      toast.error("Не удалось загрузить объект", { description: err?.message })
      router.push(`/spaces/${objectId}`)
    })
  }, [objectId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleStatusChange = (value: string) => {
    setFormData((prev) => ({ ...prev, status: value }))
  }

  const handlePhotosChange = (links: string[]) => {
    setFormData((prev) => ({ ...prev, photos: links }))
  }

  const handleSave = async () => {
    if (!formData.name?.trim()) {
      toast.error("Укажите название бизнес-центра")
      return
    }
    if (!formData.address?.trim()) {
      toast.error("Укажите адрес бизнес-центра")
      return
    }

    setSaving(true)
    try {
      const payload: any = {
        name: formData.name,
        address: formData.address,
        description: formData.description,
        status: formData.status ?? "ACTIVE",
        photos: (formData.photos ?? []).map((u) => u.trim()).filter(Boolean),
      }

      if (isEdit) {
        await rentalObjectApi.update(objectId!, payload)
        toast.success("Бизнес-центр обновлён")
        router.push(`/spaces/${objectId}`)
      } else {
        const created = await rentalObjectApi.create(payload)
        toast.success("Бизнес-центр создан")
        router.push(`/spaces/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit) return
    if (!confirm(`Удалить бизнес-центр "${formData.name}"?`)) return
    try {
      await rentalObjectApi.delete(objectId!)
      toast.success("Бизнес-центр удалён")
      router.push("/spaces")
    } catch (err: any) {
      toast.error("Не удалось удалить", { description: err?.message })
    }
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
                  <Link href="/spaces">Бизнес-центры</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isEdit ? `Редактирование #${objectId}` : "Новый бизнес-центр"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">{isEdit ? "Редактирование бизнес-центра" : "Новый бизнес-центр"}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение информации о бизнес-центре." : "Добавьте новый бизнес-центр."}
              </p>
            </div>
            <div>
              {loading && isEdit ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <div className="grid gap-6">
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
                      placeholder="Краткое описание"
                      value={formData.description ?? ""}
                      onChange={handleInputChange}
                      rows={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="status">Статус</Label>
                    <Select value={formData.status ?? "ACTIVE"} onValueChange={handleStatusChange}>
                      <SelectTrigger>
                        <SelectValue />
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
                    description="Добавьте ссылки на изображения."
                    value={formData.photos ?? []}
                    onChange={handlePhotosChange}
                    addButtonLabel="Добавить фото"
                  />

                  <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-4">
                    {isEdit && (
                      <Button
                        variant="outline"
                        onClick={handleDelete}
                        className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 sm:mr-auto"
                      >
                        Удалить
                      </Button>
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
