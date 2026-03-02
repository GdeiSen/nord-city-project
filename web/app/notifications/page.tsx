"use client"

import * as React from "react"
import { IconSend, IconSettings } from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { MediaUploader } from "@/components/media-uploader"
import {
  NotificationDeliverySheet,
  type NotificationDeliverySelection,
} from "@/components/notification-delivery-sheet"
import { PageHeader } from "@/components/page-header"
import { SiteHeader } from "@/components/site-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SidebarInset } from "@/components/ui/sidebar"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit, useFilterPickerData } from "@/hooks"
import { notificationApi } from "@/lib/api"
import { userColumns } from "@/lib/table-configs/users"

function pluralizeDeliveryTargets(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100

  if (mod10 === 1 && mod100 !== 11) return "получатель"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "получателя"
  return "получателей"
}

function pluralizeUsers(count: number): string {
  const mod10 = count % 10
  const mod100 = count % 100

  if (mod10 === 1 && mod100 !== 11) return "пользователю"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "пользователям"
  return "пользователям"
}

function getRoleOptions() {
  const roleColumn = userColumns.find((column) => column.id === "role")
  return roleColumn?.filterSelect ?? []
}

export default function NotificationsPage() {
  const canSendNotifications = useCanEdit()
  const filterPickerData = useFilterPickerData({ users: true })
  const users = filterPickerData.users ?? []

  const [isSettingsOpen, setIsSettingsOpen] = React.useState(false)
  const [selection, setSelection] = React.useState<NotificationDeliverySelection>({
    roleIds: [],
    userIds: [],
  })
  const [title, setTitle] = React.useState("")
  const [message, setMessage] = React.useState("")
  const [imageUrls, setImageUrls] = React.useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const roleOptions = React.useMemo(() => getRoleOptions(), [])

  const roleLabels = React.useMemo(() => {
    const map = new Map<string, string>()
    roleOptions.forEach((option) => {
      map.set(option.value, option.label)
    })
    return map
  }, [roleOptions])

  const userLabels = React.useMemo(() => {
    const map = new Map<number, string>()
    users.forEach((user) => {
      const name = `${user.last_name ?? ""} ${user.first_name ?? ""}`.trim()
      const username = user.username ? `@${user.username}` : ""
      map.set(user.id, `${name} ${username}`.trim() || `#${user.id}`)
    })
    return map
  }, [users])

  const estimatedRecipientIds = React.useMemo(() => {
    const recipientIds = new Set<number>()
    const selectedRoles = new Set(selection.roleIds)

    if (selectedRoles.size > 0) {
      users.forEach((user) => {
        if (user.role != null && selectedRoles.has(user.role)) {
          recipientIds.add(user.id)
        }
      })
    }

    selection.userIds.forEach((userId) => recipientIds.add(userId))
    return Array.from(recipientIds)
  }, [selection.roleIds, selection.userIds, users])

  const summaryText = React.useMemo(() => {
    if (selection.roleIds.length === 0 && selection.userIds.length === 0) {
      return "Получатели не выбраны. Откройте «Настройка отправки», чтобы выбрать роли или конкретных пользователей."
    }

    const summaryParts: string[] = []
    if (selection.roleIds.length > 0) {
      const selectedRoleLabels = selection.roleIds.map(
        (roleId) => roleLabels.get(String(roleId)) ?? `Роль #${roleId}`
      )
      summaryParts.push(`по ролям: ${selectedRoleLabels.join(", ")}`)
    }

    if (selection.userIds.length > 0) {
      const selectedUsers = selection.userIds.map(
        (userId) => userLabels.get(userId) ?? `#${userId}`
      )
      summaryParts.push(`вручную добавлены: ${selectedUsers.join(", ")}`)
    }

    const recipientCount = estimatedRecipientIds.length
    return `Сообщение будет отправлено ${summaryParts.join("; ")}. Предварительно: ${recipientCount} ${pluralizeDeliveryTargets(recipientCount)}. Повторы будут удалены автоматически.`
  }, [estimatedRecipientIds.length, roleLabels, selection.roleIds, selection.userIds, userLabels])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isSubmitting) return

    if (selection.roleIds.length === 0 && selection.userIds.length === 0) {
      toast.error("Сначала выберите получателей")
      return
    }

    const trimmedTitle = title.trim()
    const trimmedMessage = message.trim()
    if (!trimmedTitle || !trimmedMessage) {
      toast.error("Заполните заголовок и текст сообщения")
      return
    }

    setIsSubmitting(true)
    try {
      const result = await notificationApi.send({
        role_ids: selection.roleIds,
        user_ids: selection.userIds,
        title: trimmedTitle,
        message: trimmedMessage,
        image_urls: imageUrls,
      })

      if (result.sent_count === 0 && result.failed_count > 0) {
        toast.error("Сообщение не доставлено", {
          description: `Не удалось отправить ${result.failed_count} из ${result.resolved_recipient_count} получателей.`,
        })
      } else if (result.failed_count > 0) {
        toast.success("Отправка завершена частично", {
          description: `Доставлено: ${result.sent_count}. Ошибок: ${result.failed_count}.`,
        })
      } else {
        toast.success("Уведомление отправлено", {
          description: `Сообщение доставлено ${result.sent_count} ${pluralizeUsers(result.sent_count)}.`,
        })
      }

      setTitle("")
      setMessage("")
      setImageUrls([])
    } catch (error: any) {
      toast.error("Не удалось отправить уведомление", {
        description: error?.message ?? "Попробуйте еще раз.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Оповещение пользователей"
            description="Отправка объявлений пользователям через bot_service с поддержкой изображений"
          />

          {!canSendNotifications ? (
            <Alert variant="destructive">
              <AlertTitle>Доступ ограничен</AlertTitle>
              <AlertDescription>
                Отправка уведомлений доступна только администраторам и super admin.
              </AlertDescription>
            </Alert>
          ) : (
            <form onSubmit={handleSubmit}>
              <Card>
                <CardHeader>
                  <CardTitle>Новое уведомление</CardTitle>
                  <CardDescription>
                    Настройте аудиторию, заполните сообщение и при необходимости прикрепите изображения из media service.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-3">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setIsSettingsOpen(true)}
                      className="w-full justify-start sm:w-auto"
                    >
                      <IconSettings className="h-4 w-4" />
                      Настройка отправки
                    </Button>
                    <div className="rounded-lg border border-dashed bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                      {summaryText}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notification-title">Заголовок сообщения</Label>
                    <Input
                      id="notification-title"
                      value={title}
                      onChange={(event) => setTitle(event.target.value)}
                      placeholder="Например: Плановое отключение воды"
                      maxLength={160}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="notification-message">Текст сообщения</Label>
                    <Textarea
                      id="notification-message"
                      value={message}
                      onChange={(event) => setMessage(event.target.value)}
                      placeholder="Опишите, что произошло, когда и что нужно сделать пользователям."
                      rows={8}
                      maxLength={4000}
                    />
                  </div>

                  <MediaUploader
                    value={imageUrls}
                    onChange={setImageUrls}
                    label="Изображения"
                    description="Используется существующий media uploader: изображения загружаются в media_service и затем прикрепляются к уведомлению."
                  />
                </CardContent>
                <CardFooter className="justify-end">
                  <Button
                    type="submit"
                    disabled={
                      isSubmitting ||
                      (selection.roleIds.length === 0 && selection.userIds.length === 0) ||
                      !title.trim() ||
                      !message.trim()
                    }
                  >
                    <IconSend className="h-4 w-4" />
                    {isSubmitting ? "Отправка..." : "Отправить уведомление"}
                  </Button>
                </CardFooter>
              </Card>
            </form>
          )}
        </div>
      </SidebarInset>

      <NotificationDeliverySheet
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
        value={selection}
        users={users}
        roleOptions={roleOptions}
        onApply={setSelection}
      />
      <Toaster />
    </>
  )
}
