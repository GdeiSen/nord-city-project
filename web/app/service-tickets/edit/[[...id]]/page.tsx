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
import { ServiceTicket, User, RentalObject, TICKET_STATUS } from "@/types"
import { serviceTicketApi, userApi, rentalObjectApi } from "@/lib/api"
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

export default function ServiceTicketEditPage() {
  const router = useRouter()
  const { id: ticketId, isEdit } = useRouteId({ paramKey: "id", parseMode: "number" })

  const { loading, withLoading } = useLoading(true)
  const [users, setUsers] = useState<User[]>([])
  const [objects, setObjects] = useState<RentalObject[]>([])
  const [formData, setFormData] = useState<Partial<ServiceTicket>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const load = async () => {
      const [allUsers, allObjects] = await Promise.all([userApi.getAll(), rentalObjectApi.getAll()])
      setUsers(allUsers)
      setObjects(allObjects)
      if (isEdit) {
        const ticket = await serviceTicketApi.getById(Number(ticketId!))
        const user = allUsers.find((u) => u.id === ticket.user_id)
        setFormData({
          ...ticket,
          user: user || undefined,
        })
      } else {
        setFormData({})
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/service-tickets/${Number(ticketId!)}`)
      else router.push("/service-tickets")
    })
  }, [ticketId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSelectChange = (name: string, value: string) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const allowedFields = [
        "user_id", "object_id", "description", "location", "image", "status", "ddid",
        "answer", "header", "details", "msid", "meta",
      ] as const
      const payload: Record<string, unknown> = {}
      for (const key of allowedFields) {
        let val: unknown = (formData as any)[key]
        if (key === "user_id" && (val === undefined || val === null)) {
          val = (formData as any).user?.id
        }
        if (val !== undefined && val !== null) {
          payload[key] = val
        }
      }
      if (isEdit) {
        await serviceTicketApi.update(Number(ticketId!), payload as any)
        toast.success("Заявка обновлена")
        router.push(`/service-tickets/${Number(ticketId!)}`)
      } else {
        if (!payload.user_id) {
          toast.error("Выберите пользователя")
          setSaving(false)
          return
        }
        if (!payload.ddid) payload.ddid = "0000-0000-0000"
        const created = await serviceTicketApi.create(payload as any)
        toast.success("Заявка создана")
        router.push(`/service-tickets/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить заявку", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit) return
    try {
      await serviceTicketApi.delete(Number(ticketId!))
      toast.success("Заявка удалена")
      router.push("/service-tickets")
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
                  <Link href="/service-tickets">Заявки</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isEdit ? `Редактирование #${ticketId}` : "Новая заявка"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">{isEdit ? "Редактирование заявки" : "Создание заявки"}</h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение информации о заявке." : "Создайте новую заявку на обслуживание."}
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
                    <Label htmlFor="description">Описание</Label>
                    <Textarea
                      id="description"
                      name="description"
                      value={formData.description ?? ""}
                      onChange={handleInputChange}
                      rows={4}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Местоположение</Label>
                    <Input id="location" name="location" value={formData.location ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="status">Статус</Label>
                    <Select value={formData.status ?? ""} onValueChange={(v) => handleSelectChange("status", v)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Выберите статус" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={TICKET_STATUS.NEW}>Новая</SelectItem>
                        <SelectItem value={TICKET_STATUS.ACCEPTED}>Принята</SelectItem>
                        <SelectItem value={TICKET_STATUS.ASSIGNED}>В работе</SelectItem>
                        <SelectItem value={TICKET_STATUS.COMPLETED}>Завершена</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="user_id">Пользователь</Label>
                    <EntityPicker<User>
                      dataConfig={{
                        data: users,
                        getValue: (u) => u.id,
                        getLabel: (u) => {
                          const name = `${u.last_name ?? ""} ${u.first_name ?? ""}`.trim()
                          return name
                            ? `${name}${u.username ? ` (@${u.username})` : ""}`
                            : (u.username ? `@${u.username}` : `#${u.id}`)
                        },
                      }}
                      value={formData.user_id ?? null}
                      onSelect={(user) => setFormData((prev) => ({ ...prev, user_id: user.id }))}
                      placeholder="Не назначен"
                    />
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
