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
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Feedback } from "@/types"
import { feedbackApi } from "@/lib/api"
import { useLoading } from "@/hooks/use-loading"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

export default function FeedbackEditPage() {
  const params = useParams<{ id?: string[] }>()
  const router = useRouter()
  const idParam = params?.id?.[0]
  const feedbackId = idParam ? parseInt(idParam, 10) : null
  const isEdit = feedbackId != null && !Number.isNaN(feedbackId)

  const { loading, withLoading } = useLoading(true)
  const [formData, setFormData] = useState<Partial<Feedback>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!isEdit) {
      setFormData({})
      return
    }
    withLoading(async () => {
      const data = await feedbackApi.getById(feedbackId!)
      setFormData(data)
    }).catch((err: any) => {
      toast.error("Не удалось загрузить отзыв", { description: err?.message })
      router.push(`/feedbacks/${feedbackId}`)
    })
  }, [feedbackId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    if (!isEdit) return
    setSaving(true)
    try {
      const payload: any = { ...formData }
      delete payload.id
      delete payload.user
      delete payload.created_at
      delete payload.updated_at

      await feedbackApi.update(feedbackId!, payload)
      toast.success("Отзыв обновлён")
      router.push(`/feedbacks/${feedbackId}`)
    } catch (err: any) {
      toast.error("Не удалось сохранить отзыв", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit) return
    if (!confirm("Удалить этот отзыв?")) return
    try {
      await feedbackApi.delete(feedbackId!)
      toast.success("Отзыв удалён")
      router.push("/feedbacks")
    } catch (err: any) {
      toast.error("Не удалось удалить отзыв", { description: err?.message })
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
                      <Button
                        variant="outline"
                        onClick={handleDelete}
                        className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 sm:mr-auto"
                      >
                        Удалить
                      </Button>
                      <Button onClick={handleSave} disabled={saving}>
                        {saving ? "Сохранение..." : "Сохранить"}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {!isEdit && (
            <div className="max-w-2xl space-y-4 py-8">
              <p className="text-muted-foreground">Создание отзывов через эту панель не поддерживается.</p>
              <Link href="/feedbacks" className="text-sm text-primary hover:underline">
                К списку отзывов
              </Link>
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
