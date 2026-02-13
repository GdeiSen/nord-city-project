"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
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
import { IconChevronLeft } from "@tabler/icons-react"
import { ServiceTicket, User, TICKET_STATUS, TICKET_PRIORITY } from "@/types"
import { serviceTicketApi, userApi } from "@/lib/api"
import { DataPicker, DataPickerField } from "@/components/data-picker"
import { useLoading } from "@/hooks/use-loading"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

const userFields: DataPickerField[] = [
  { key: "first_name", label: "Имя", searchable: true },
  { key: "last_name", label: "Фамилия", searchable: true },
  { key: "username", label: "Username", searchable: true },
  { key: "email", label: "Email", searchable: true },
  { key: "id", label: "ID", render: (value) => <span className="text-right">#{value}</span> },
]

export default function ServiceTicketEditPage() {
  const params = useParams<{ id?: string[] }>()
  const router = useRouter()
  const idParam = params?.id?.[0]
  const ticketId = idParam ? parseInt(idParam, 10) : null
  const isEdit = ticketId != null && !Number.isNaN(ticketId)

  const { loading, withLoading } = useLoading(true)
  const [users, setUsers] = useState<User[]>([])
  const [formData, setFormData] = useState<Partial<ServiceTicket>>({})
  const [saving, setSaving] = useState(false)
  const [isUserPickerOpen, setIsUserPickerOpen] = useState(false)

  useEffect(() => {
    const load = async () => {
      const allUsers = await userApi.getAll()
      setUsers(allUsers)
      if (isEdit) {
        const ticket = await serviceTicketApi.getById(ticketId!)
        const user = allUsers.find((u) => u.id === ticket.user_id)
        setFormData({
          ...ticket,
          user: user || undefined,
        })
      } else {
        setFormData({ priority: 1 })
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/service-tickets/${ticketId}`)
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
      const payload: any = {
        ...formData,
        user_id: formData.user_id ?? (formData as any).user?.id,
        priority: typeof formData.priority === "string" ? parseInt(String(formData.priority), 10) : formData.priority ?? 1,
      }
      delete payload.user
      delete payload.id
      delete payload.created_at
      delete payload.updated_at

      if (isEdit) {
        await serviceTicketApi.update(ticketId!, payload)
        toast.success("Заявка обновлена")
        router.push(`/service-tickets/${ticketId}`)
      } else {
        if (!payload.ddid) payload.ddid = "0000-0000-0000"
        const created = await serviceTicketApi.create(payload)
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
    if (!confirm("Удалить эту заявку?")) return
    try {
      await serviceTicketApi.delete(ticketId!)
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
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
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

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href={isEdit ? `/service-tickets/${ticketId}` : "/service-tickets"} className="gap-2">
                <IconChevronLeft className="h-4 w-4" />
                Назад
              </Link>
            </Button>
          </div>

          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>{isEdit ? "Редактирование заявки" : "Создание заявки"}</CardTitle>
              <CardDescription>
                {isEdit ? "Изменение информации о заявке." : "Создайте новую заявку на обслуживание."}
              </CardDescription>
            </CardHeader>
            <CardContent>
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
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="priority">Приоритет</Label>
                      <Select
                        value={String(formData.priority ?? "")}
                        onValueChange={(v) => handleSelectChange("priority", v)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Выберите приоритет" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={String(TICKET_PRIORITY.LOW)}>Низкий</SelectItem>
                          <SelectItem value={String(TICKET_PRIORITY.MEDIUM)}>Средний</SelectItem>
                          <SelectItem value={String(TICKET_PRIORITY.HIGH)}>Высокий</SelectItem>
                          <SelectItem value={String(TICKET_PRIORITY.CRITICAL)}>Критический</SelectItem>
                        </SelectContent>
                      </Select>
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
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="user_id">Пользователь</Label>
                    <DataPicker
                      title="Выбор пользователя"
                      description="Найдите пользователя по имени, email или username."
                      data={users}
                      fields={userFields}
                      value={formData.user_id}
                      displayValue={
                        formData.user_id
                          ? (() => {
                              const user = users.find((u) => u.id === formData.user_id)
                              return user ? `${user.last_name} ${user.first_name} (@${user.username})` : `User #${formData.user_id}`
                            })()
                          : undefined
                      }
                      placeholder="Не назначен"
                      onSelect={(user: User) => setFormData((prev) => ({ ...prev, user_id: user.id }))}
                      open={isUserPickerOpen}
                      onOpenChange={setIsUserPickerOpen}
                    />
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
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
