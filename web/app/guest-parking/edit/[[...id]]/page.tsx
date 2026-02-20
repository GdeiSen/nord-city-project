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
import { GuestParkingRequest, User } from "@/types"
import { guestParkingApi, userApi } from "@/lib/api"
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

/** Форматирует datetime в date и time для input[type=date] и input[type=time] */
function splitDateTime(iso: string | undefined): { date: string; time: string } {
  if (!iso) {
    const now = new Date()
    return {
      date: now.toISOString().slice(0, 10),
      time: "09:00",
    }
  }
  const d = new Date(iso)
  const date = d.toISOString().slice(0, 10)
  const time = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
  return { date, time }
}

function toISOString(date: string, time: string): string {
  return `${date}T${time}:00`
}

export default function GuestParkingEditPage() {
  const router = useRouter()
  const { id: reqId, isEdit } = useRouteId({ paramKey: "id", parseMode: "number" })

  const { loading, withLoading } = useLoading(true)
  const [users, setUsers] = useState<User[]>([])
  const [formData, setFormData] = useState<{
    user_id: number | null
    arrival_date: string
    arrival_time: string
    license_plate: string
    car_make_color: string
    driver_phone: string
    tenant_phone: string
  }>({
    user_id: null,
    arrival_date: "",
    arrival_time: "09:00",
    license_plate: "",
    car_make_color: "",
    driver_phone: "",
    tenant_phone: "",
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const load = async () => {
      const allUsers = await userApi.getAll()
      setUsers(allUsers)
      if (isEdit && reqId) {
        const req = await guestParkingApi.getById(Number(reqId))
        const { date, time } = splitDateTime(req.arrival_date)
        setFormData({
          user_id: req.user_id,
          arrival_date: date,
          arrival_time: time,
          license_plate: req.license_plate ?? "",
          car_make_color: req.car_make_color ?? "",
          driver_phone: req.driver_phone ?? "",
          tenant_phone: req.tenant_phone ?? "",
        })
      } else {
        const now = new Date()
        setFormData((prev) => ({
          ...prev,
          arrival_date: now.toISOString().slice(0, 10),
          arrival_time: "09:00",
        }))
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/guest-parking/${Number(reqId!)}`)
      else router.push("/guest-parking")
    })
  }, [reqId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    if (!formData.user_id) {
      toast.error("Выберите арендатора")
      return
    }
    if (!formData.license_plate?.trim()) {
      toast.error("Укажите госномер")
      return
    }
    if (!formData.car_make_color?.trim()) {
      toast.error("Укажите марку и цвет автомобиля")
      return
    }
    if (!formData.driver_phone?.trim()) {
      toast.error("Укажите телефон водителя")
      return
    }
    setSaving(true)
    try {
      const arrivalDate = toISOString(formData.arrival_date, formData.arrival_time)
      if (isEdit && reqId) {
        await guestParkingApi.update(Number(reqId), {
          user_id: formData.user_id,
          arrival_date: arrivalDate,
          license_plate: formData.license_plate.trim(),
          car_make_color: formData.car_make_color.trim(),
          driver_phone: formData.driver_phone.trim(),
          tenant_phone: formData.tenant_phone.trim() || undefined,
        } as any)
        toast.success("Заявка обновлена")
        router.push(`/guest-parking/${Number(reqId)}`)
      } else {
        const created = await guestParkingApi.create({
          user_id: formData.user_id,
          arrival_date: arrivalDate,
          license_plate: formData.license_plate.trim(),
          car_make_color: formData.car_make_color.trim(),
          driver_phone: formData.driver_phone.trim(),
          tenant_phone: formData.tenant_phone.trim() || undefined,
        } as any)
        toast.success("Заявка создана")
        router.push(`/guest-parking/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить заявку", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit || !reqId) return
    try {
      await guestParkingApi.delete(Number(reqId))
      toast.success("Заявка удалена")
      router.push("/guest-parking")
    } catch (err: any) {
      toast.error("Не удалось удалить заявку", { description: err?.message })
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
                <BreadcrumbPage>{isEdit ? `Редактирование #${reqId}` : "Новая заявка"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">
                {isEdit ? "Редактирование заявки" : "Создание заявки"}
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение данных заявки. Сообщение в чате администраторов обновится." : "Создайте заявку на гостевую парковку. Уведомление будет отправлено в чат администраторов."}
              </p>
            </div>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : (
              <div className="grid gap-6">
                <div className="space-y-2">
                  <Label>Арендатор</Label>
                  <EntityPicker<User>
                    dataConfig={{
                      data: users,
                      getValue: (u) => u.id,
                      getLabel: (u) => {
                        const name = `${u.last_name ?? ""} ${u.first_name ?? ""}`.trim()
                        return name ? `${name}${u.username ? ` (@${u.username})` : ""}` : (u.username ? `@${u.username}` : `#${u.id}`)
                      },
                    }}
                    value={formData.user_id}
                    onSelect={(u) => setFormData((prev) => ({ ...prev, user_id: u.id }))}
                    placeholder="Выберите арендатора"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="arrival_date">Дата заезда</Label>
                    <Input
                      id="arrival_date"
                      name="arrival_date"
                      type="date"
                      value={formData.arrival_date}
                      onChange={handleInputChange}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="arrival_time">Время заезда</Label>
                    <Input
                      id="arrival_time"
                      name="arrival_time"
                      type="time"
                      value={formData.arrival_time}
                      onChange={handleInputChange}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="license_plate">Госномер</Label>
                  <Input
                    id="license_plate"
                    name="license_plate"
                    value={formData.license_plate}
                    onChange={handleInputChange}
                    placeholder="А123БВ77"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="car_make_color">Марка и цвет автомобиля</Label>
                  <Input
                    id="car_make_color"
                    name="car_make_color"
                    value={formData.car_make_color}
                    onChange={handleInputChange}
                    placeholder="Toyota Corolla, белый"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="driver_phone">Телефон водителя</Label>
                  <Input
                    id="driver_phone"
                    name="driver_phone"
                    type="tel"
                    value={formData.driver_phone}
                    onChange={handleInputChange}
                    placeholder="+375291234567"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tenant_phone">Телефон арендатора</Label>
                  <Input
                    id="tenant_phone"
                    name="tenant_phone"
                    type="tel"
                    value={formData.tenant_phone}
                    onChange={handleInputChange}
                    placeholder="+375291234567"
                  />
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
                          <AlertDialogTitle>Удалить эту заявку?</AlertDialogTitle>
                          <AlertDialogDescription>
                            Сообщение в чате администраторов будет удалено.
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
      </SidebarInset>
      <Toaster />
    </>
  )
}
