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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { User, USER_ROLES, ROLE_LABELS, RentalObject } from "@/types"
import { userApi, rentalObjectApi } from "@/lib/api"
import { DataPicker, DataPickerField } from "@/components/data-picker"
import { useLoading } from "@/hooks/use-loading"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

const objectFields: DataPickerField[] = [
  { key: "name", label: "Название", searchable: true },
  { key: "address", label: "Адрес", searchable: true },
  { key: "id", label: "ID", render: (value) => <span className="text-right">{value}</span> },
]

export default function UserEditPage() {
  const params = useParams<{ id?: string[] }>()
  const router = useRouter()
  const idParam = params?.id?.[0]
  const userId = idParam ? parseInt(idParam, 10) : null
  const isEdit = userId != null && !Number.isNaN(userId)

  const { loading, withLoading } = useLoading(true)
  const [objects, setObjects] = useState<RentalObject[]>([])
  const [formData, setFormData] = useState<Partial<User>>({})
  const [saving, setSaving] = useState(false)
  const [isObjectPickerOpen, setIsObjectPickerOpen] = useState(false)

  useEffect(() => {
    const load = async () => {
      const allObjects = await rentalObjectApi.getAll()
      setObjects(allObjects)
      if (isEdit) {
        const userData = await userApi.getById(userId!)
        setFormData(userData)
      } else {
        setFormData({ language_code: "ru" })
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/users/${userId}`)
      else router.push("/users")
    })
  }, [userId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSelectChange = (name: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [name]: name === "role" ? parseInt(value, 10) : value,
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload: any = { ...formData }
      delete payload.id
      delete payload.created_at
      delete payload.updated_at
      delete payload.object

      if (isEdit) {
        await userApi.update(userId!, payload)
        toast.success("Пользователь обновлён")
        router.push(`/users/${userId}`)
      } else {
        const created = await userApi.create(payload)
        toast.success("Пользователь создан")
        router.push(`/users/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить пользователя", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit) return
    if (!confirm("Удалить этого пользователя?")) return
    try {
      await userApi.delete(userId!)
      toast.success("Пользователь удалён")
      router.push("/users")
    } catch (err: any) {
      toast.error("Не удалось удалить пользователя", { description: err?.message })
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
                  <Link href="/users">Пользователи</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isEdit ? `Редактирование #${userId}` : "Новый пользователь"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">{isEdit ? "Редактирование пользователя" : "Новый пользователь"}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение данных пользователя." : "Создание учётной записи."}
              </p>
            </div>
            <div>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              ) : (
                <div className="grid gap-6">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="first_name">Имя</Label>
                      <Input id="first_name" name="first_name" value={formData.first_name ?? ""} onChange={handleInputChange} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="last_name">Фамилия</Label>
                      <Input id="last_name" name="last_name" value={formData.last_name ?? ""} onChange={handleInputChange} />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="middle_name">Отчество</Label>
                    <Input id="middle_name" name="middle_name" value={formData.middle_name ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username">Username</Label>
                    <Input id="username" name="username" value={formData.username ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" name="email" type="email" value={formData.email ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone_number">Телефон</Label>
                    <Input id="phone_number" name="phone_number" value={formData.phone_number ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="role">Роль</Label>
                      <Select value={formData.role?.toString() ?? ""} onValueChange={(v) => handleSelectChange("role", v)}>
                        <SelectTrigger>
                          <SelectValue placeholder="Выберите роль" />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(USER_ROLES).map(([key, value]) => (
                            <SelectItem key={key} value={value.toString()}>
                              {ROLE_LABELS[value]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="language_code">Язык</Label>
                      <Select value={formData.language_code ?? "ru"} onValueChange={(v) => handleSelectChange("language_code", v)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ru">Русский</SelectItem>
                          <SelectItem value="en">English</SelectItem>
                          <SelectItem value="kz">Қазақша</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Объект</Label>
                    <DataPicker
                      title="Выбор объекта"
                      description="Найдите объект по названию или адресу."
                      data={objects}
                      fields={objectFields}
                      value={formData.object_id}
                      displayValue={
                        formData.object_id
                          ? (() => {
                              const obj = objects.find((o) => o.id === formData.object_id)
                              return obj ? `${obj.name} (БЦ-${obj.id})` : `БЦ-${formData.object_id}`
                            })()
                          : undefined
                      }
                      placeholder="Не назначен"
                      onSelect={(obj: RentalObject) => setFormData((prev) => ({ ...prev, object_id: obj.id }))}
                      open={isObjectPickerOpen}
                      onOpenChange={setIsObjectPickerOpen}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="legal_entity">Юр. лицо</Label>
                    <Input id="legal_entity" name="legal_entity" value={formData.legal_entity ?? ""} onChange={handleInputChange} />
                  </div>

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
