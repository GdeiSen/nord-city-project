"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Feedback, User } from "@/types"
import { feedbackApi, userApi } from "@/lib/api"
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
import { useRouteId, useEntityForm, useIsSuperAdmin } from "@/hooks"
import { Toaster } from "@/components/ui/sonner"

export default function FeedbackEditPage() {
  const isSuperAdmin = useIsSuperAdmin()
  const { id: feedbackId, isEdit } = useRouteId({ paramKey: "id", parseMode: "number" })
  const entityId = typeof feedbackId === "number" ? feedbackId : null

  const {
    loading,
    formData,
    saving,
    handleInputChange,
    handleSelectChange,
    handleSave,
    handleDelete,
  } = useEntityForm<Feedback>({
    entityId,
    isEdit,
    fetchInitial: async () => {
      if (!isEdit) return {}
      return feedbackApi.getById(entityId!)
    },
    defaultValues: {},
    preparePayload: (data) => {
      const payload = { ...data }
      delete (payload as Record<string, unknown>).id
      delete (payload as Record<string, unknown>).user
      delete (payload as Record<string, unknown>).created_at
      delete (payload as Record<string, unknown>).updated_at
      return payload as Record<string, unknown>
    },
    onCreate: async (payload) => {
      const created = await feedbackApi.create(payload as Record<string, unknown>)
      return { id: created.id }
    },
    onUpdate: (id, payload) => feedbackApi.update(id, payload as Partial<Feedback>),
    onDelete: (id) => feedbackApi.delete(id),
    createRedirect: () => "/feedbacks",
    updateRedirect: (id) => `/feedbacks/${id}`,
    deleteRedirect: "/feedbacks",
    errorMessages: {
      load: "Не удалось загрузить отзыв",
      save: "Не удалось сохранить отзыв",
      delete: "Не удалось удалить отзыв",
    },
    successMessages: {
      save: "Отзыв обновлён",
      create: "Отзыв создан",
      delete: "Отзыв удалён",
    },
    onLoadErrorRedirect: () => `/feedbacks/${entityId}`,
  })

  const [users, setUsers] = useState<User[]>([])
  useEffect(() => {
    userApi.getAll().then(setUsers).catch(() => {})
  }, [])

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
                  <Link href="/feedbacks">Отзывы</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isEdit ? `Редактирование #${feedbackId}` : "Отзыв"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          {isEdit && (
            isSuperAdmin ? (
            <div className="max-w-2xl space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Редактирование отзыва</h1>
                <p className="text-sm text-muted-foreground mt-1">Изменение информации об отзыве.</p>
              </div>
              <div>
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                  </div>
                ) : (
                  <div className="grid gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="answer">Ответ</Label>
                      <Input id="answer" name="answer" value={formData.answer ?? ""} onChange={handleInputChange} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="text">Текст</Label>
                      <Textarea id="text" name="text" value={formData.text ?? ""} onChange={handleInputChange} rows={4} />
                    </div>

                    <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-4">
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
                            <AlertDialogTitle>Удалить этот отзыв?</AlertDialogTitle>
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
                      <Button onClick={handleSave} disabled={saving}>
                        {saving ? "Сохранение..." : "Сохранить"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
            ) : (
              <div className="max-w-2xl space-y-4 py-8">
                <p className="text-muted-foreground">Редактирование отзывов доступно только для Super Admin.</p>
                <Link href="/feedbacks" className="text-sm text-primary hover:underline">
                  К списку отзывов
                </Link>
              </div>
            )
          )}

          {!isEdit && (
            isSuperAdmin ? (
              <div className="max-w-2xl space-y-6">
                <div>
                  <h1 className="text-2xl font-semibold">Создание отзыва</h1>
                  <p className="text-sm text-muted-foreground mt-1">Добавление нового отзыва от имени пользователя.</p>
                </div>
                <div className="grid gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="user_id">Пользователь</Label>
                    <EntityPicker<User>
                      value={formData.user_id ?? null}
                      onSelect={(user) => handleSelectChange("user_id", user.id)}
                      dataConfig={{
                        data: users,
                        getValue: (u) => u.id,
                        getLabel: (u) => {
                          const name = `${u.last_name ?? ""} ${u.first_name ?? ""}`.trim()
                          return name ? `${name}${u.username ? ` (@${u.username})` : ""}` : (u.username ? `@${u.username}` : `#${u.id}`)
                        },
                      }}
                      placeholder="Выберите пользователя"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ddid">DDID (0000-0000-0000)</Label>
                    <Input
                      id="ddid"
                      name="ddid"
                      value={formData.ddid ?? ""}
                      onChange={handleInputChange}
                      placeholder="0000-0000-0000"
                      maxLength={14}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="answer">Ответ</Label>
                    <Input id="answer" name="answer" value={formData.answer ?? ""} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="text">Текст (необязательно)</Label>
                    <Textarea id="text" name="text" value={formData.text ?? ""} onChange={handleInputChange} rows={4} />
                  </div>
                  <div className="flex justify-end pt-4">
                    <Button onClick={handleSave} disabled={saving}>
                      {saving ? "Создание..." : "Создать"}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="max-w-2xl space-y-4 py-8">
                <p className="text-muted-foreground">Создание отзывов доступно только для Super Admin.</p>
                <Link href="/feedbacks" className="text-sm text-primary hover:underline">
                  К списку отзывов
                </Link>
              </div>
            )
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
