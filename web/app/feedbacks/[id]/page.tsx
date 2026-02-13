"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { IconEdit } from "@tabler/icons-react"
import { Feedback } from "@/types"
import { feedbackApi, userApi } from "@/lib/api"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function FeedbackDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const feedbackId = Number(params?.id)
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  useEffect(() => {
    if (!feedbackId || Number.isNaN(feedbackId)) return
    withLoading(async () => {
      const [feedbackData, users] = await Promise.all([
        feedbackApi.getById(feedbackId),
        userApi.getAll(),
      ])
      const user = users.find((u) => u.id === feedbackData.user_id)
      setFeedback({
        ...feedbackData,
        user: user || ({ first_name: "", last_name: "", username: "" } as any),
      })
    }).catch((err: any) => {
      toast.error("Не удалось загрузить отзыв", { description: err?.message })
      router.push("/feedbacks")
    })
  }, [feedbackId])

  if (Number.isNaN(feedbackId)) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
            <p className="text-lg font-medium">Отзыв не найден</p>
            <p className="text-sm text-muted-foreground">Некорректный идентификатор.</p>
            <Link href="/feedbacks" className="text-sm text-primary hover:underline">
              К списку отзывов
            </Link>
          </div>
        </SidebarInset>
        <Toaster />
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink asChild>
                    <Link href="/feedbacks">Отзывы</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>#{feedbackId}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            {canEdit && (
              <Button asChild size="sm">
                <Link href={`/feedbacks/edit/${feedbackId}`} className="gap-2">
                  <IconEdit className="h-4 w-4" />
                  Редактировать
                </Link>
              </Button>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : feedback ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Отзыв #{feedback.id}</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  {formatDate(feedback.created_at)}
                  {feedback.updated_at !== feedback.created_at && (
                    <> · Обновлён {formatDate(feedback.updated_at)}</>
                  )}
                </p>
              </div>
              <div className="space-y-6">
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Пользователь</div>
                  <p className="text-sm font-medium">
                    {feedback.user?.last_name} {feedback.user?.first_name}{" "}
                    {feedback.user?.username ? `(@${feedback.user.username})` : ""}
                  </p>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Ответ</div>
                  <p className="text-sm">{feedback.answer || "—"}</p>
                </div>
                {feedback.text && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Текст</div>
                    <p className="text-sm whitespace-pre-wrap">{feedback.text}</p>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
