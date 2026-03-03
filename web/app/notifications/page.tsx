"use client"

import * as React from "react"
import { IconSend, IconSettings } from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { StorageUploader } from "@/components/storage-uploader"
import {
  NotificationDeliverySheet,
  type NotificationDeliverySelection,
} from "@/components/notification-delivery-sheet"
import { SiteHeader } from "@/components/site-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SidebarInset } from "@/components/ui/sidebar"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit, useFilterPickerData } from "@/hooks"
import { notificationApi } from "@/lib/api"
import { userColumns } from "@/lib/table-configs/users"

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
  const [attachmentUrls, setAttachmentUrls] = React.useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const roleOptions = React.useMemo(() => getRoleOptions(), [])

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
        attachment_urls: attachmentUrls,
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
      setAttachmentUrls([])
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
          {!canSendNotifications ? (
            <Alert variant="destructive">
              <AlertTitle>Доступ ограничен</AlertTitle>
              <AlertDescription>
                Отправка уведомлений доступна только администраторам и super admin.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="max-w-2xl space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Оповещение пользователей</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Подготовьте объявление и отправьте его выбранным пользователям через бота.
                </p>
              </div>

              <form onSubmit={handleSubmit}>
                <div className="grid gap-6">
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

                  <StorageUploader
                    value={attachmentUrls}
                    onChange={setAttachmentUrls}
                    label="Вложения"
                    description="Поддерживаются изображения и документы: PDF, DOCX, TXT, MD, Excel."
                    category="SYSTEM"
                  />

                  <div className="flex justify-end pt-4">
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
                  </div>
                </div>
              </form>
            </div>
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
