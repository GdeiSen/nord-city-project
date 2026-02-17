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
import { getUser } from "@/lib/auth"
import { EntityPicker } from "@/components/entity-picker"
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
import { useLoading, useRouteId } from "@/hooks"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

export default function UserEditPage() {
  const router = useRouter()
  const { id: userId, isEdit } = useRouteId({ paramKey: "id", parseMode: "number" })
  const currentUser = getUser()
  const isEditingSelf =
    isEdit &&
    currentUser?.id != null &&
    Number(userId) === currentUser.id

  const roleOptions = Object.entries(USER_ROLES)
    .filter(([_, roleValue]) => {
      if (currentUser?.role === USER_ROLES.ADMIN && roleValue === USER_ROLES.SUPER_ADMIN) {
        return false
      }
      return true
    })
    .map(([_, roleValue]) => ({
      value: String(roleValue),
      label: ROLE_LABELS[roleValue as keyof typeof ROLE_LABELS],
    }))

  const { loading, withLoading } = useLoading(true)
  const [objects, setObjects] = useState<RentalObject[]>([])
  const [formData, setFormData] = useState<Partial<User>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const load = async () => {
      const allObjects = await rentalObjectApi.getAll()
      setObjects(allObjects)
      if (isEdit) {
        const userData = await userApi.getById(Number(userId!))
        setFormData(userData)
      } else {
        setFormData({ language_code: "ru" })
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/users/${Number(userId!)}`)
      else router.push("/users")
    })
  }, [userId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
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
        await userApi.update(Number(userId!), payload)
        toast.success("Пользователь обновлён")
        router.push(`/users/${Number(userId!)}`)
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
    try {
      await userApi.delete(Number(userId!))
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
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
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
                    <p className="text-sm text-muted-foreground">
                      Изменение username может привести к рассинхронизации с Telegram-аккаунтом и потере возможности входа в систему. Редактируйте только при крайней необходимости.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" name="email" type="email" value={formData.email ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone_number">Телефон</Label>
                    <Input id="phone_number" name="phone_number" value={formData.phone_number ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="role">Роль</Label>
                      <EntityPicker
                        options={roleOptions}
                        value={formData.role ?? null}
                        onSelect={(v) => setFormData((prev) => ({ ...prev, role: parseInt(v, 10) }))}
                        placeholder="Выберите роль"
                        disabled={isEditingSelf}
                      />
                      {isEditingSelf && (
                        <p className="text-sm text-muted-foreground">
                          Изменение своей роли недоступно во избежание потери доступа к системе.
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label>Объект</Label>
                      <EntityPicker<RentalObject>
                        dataConfig={{
                          data: objects,
                          getValue: (o) => o.id,
                          getLabel: (o) => (o.name ? `${o.name} (БЦ-${o.id})` : `БЦ-${o.id}`),
                        }}
                        value={formData.object_id ?? null}
                        onSelect={(obj) => setFormData((prev) => ({ ...prev, object_id: obj.id }))}
                        placeholder="Не назначен"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="legal_entity">Юр. лицо</Label>
                    <Input id="legal_entity" name="legal_entity" value={formData.legal_entity ?? ""} onChange={handleInputChange} />
                  </div>

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
                            <AlertDialogTitle>Удалить этого пользователя?</AlertDialogTitle>
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
