"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit } from "@tabler/icons-react"
import { Feedback, FEEDBACK_TYPES, FEEDBACK_TYPE_LABELS_RU } from "@/types"
import { feedbackApi } from "@/lib/api"
import { formatDate } from "@/lib/date-utils"
import { useLoading, useRouteId } from "@/hooks"
import { useCanEdit } from "@/hooks"
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

export default function FeedbackDetailPage() {
  const router = useRouter()
  const { id: feedbackId } = useRouteId({ paramKey: "id", parseMode: "number" })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [feedback, setFeedback] = useState<Feedback | null>(null)

  useEffect(() => {
    if (!feedbackId || Number.isNaN(feedbackId)) return
    withLoading(async () => {
      const feedbackData = await feedbackApi.getById(Number(feedbackId))
      setFeedback(feedbackData)
    }).catch((err: any) => {
      toast.error("Не удалось загрузить отзыв", { description: err?.message })
      router.push("/feedbacks")
    })
  }, [feedbackId, router, withLoading])

  if (feedbackId == null || (typeof feedbackId === "number" && Number.isNaN(feedbackId))) {
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
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
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
            {canEdit && feedback?.feedback_type !== FEEDBACK_TYPES.SERVICE_TICKET && (
              <Button asChild size="default" className="shrink-0">
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
                  <div className="text-sm font-medium text-muted-foreground">Тип</div>
                  <Badge variant={feedback.feedback_type === FEEDBACK_TYPES.SERVICE_TICKET ? "default" : "secondary"}>
                    {FEEDBACK_TYPE_LABELS_RU[feedback.feedback_type ?? FEEDBACK_TYPES.GENERAL] ?? feedback.feedback_type}
                  </Badge>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Пользователь</div>
                  {feedback.user_id ? (
                    <Link
                      href={`/users/${feedback.user_id}`}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      {[feedback.user?.last_name, feedback.user?.first_name].filter(Boolean).join(" ").trim()
                        || (feedback.user?.username ? `@${feedback.user.username}` : `#${feedback.user_id}`)}
                    </Link>
                  ) : (
                    <p className="text-sm font-medium">—</p>
                  )}
                </div>
                {feedback.service_ticket_id && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Заявка</div>
                    <Link
                      href={`/service-tickets/${feedback.service_ticket_id}`}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      #{feedback.service_ticket_id}
                    </Link>
                    {feedback.service_ticket?.description && (
                      <p className="text-sm text-muted-foreground">{feedback.service_ticket.description}</p>
                    )}
                  </div>
                )}
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
