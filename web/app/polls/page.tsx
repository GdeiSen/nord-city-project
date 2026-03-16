"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { ColumnDef } from "@tanstack/react-table"
import { IconSettings } from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { PageHeader } from "@/components/page-header"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit } from "@/hooks"
import { formatDate } from "@/lib/date-utils"
import { pollApi } from "@/lib/api"
import { PollAnswer } from "@/types"

export default function PollsPage() {
  const router = useRouter()
  const canEdit = useCanEdit()
  const [loading, setLoading] = useState(true)
  const [polls, setPolls] = useState<PollAnswer[]>([])

  useEffect(() => {
    let active = true

    pollApi
      .getAll()
      .then((items) => {
        if (!active) return
        setPolls(Array.isArray(items) ? items : [])
      })
      .catch((error: any) => {
        toast.error("Не удалось загрузить результаты опросов", { description: error?.message })
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  const columns: ColumnDef<PollAnswer>[] = [
    createSelectColumn<PollAnswer>(),
    {
      accessorKey: "id",
      header: "ID",
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "user_id",
      header: "Пользователь",
      cell: ({ row }) => <div className="text-sm">#{row.original.user_id}</div>,
    },
    {
      accessorKey: "ddid",
      header: "Вопрос (DDID)",
      cell: ({ row }) => <div className="font-mono text-xs">{row.original.ddid}</div>,
    },
    {
      accessorKey: "answer",
      header: "Ответ",
      cell: ({ row }) => <div className="text-sm">{row.original.answer}</div>,
    },
    {
      accessorKey: "created_at",
      header: "Дата",
      cell: ({ row }) => (
        <div className="text-sm">{formatDate(row.original.created_at, { includeTime: true })}</div>
      ),
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Опросы"
            description="Результаты ответов пользователей и настройки ссылки на Google Форму."
            actions={
              canEdit ? (
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => router.push("/polls/settings")}
                  aria-label="Настройки опроса"
                >
                  <IconSettings className="h-4 w-4" />
                </Button>
              ) : undefined
            }
          />

          <DataTable
            data={polls}
            columns={columns}
            loading={loading}
            loadingMessage="Загрузка результатов опроса..."
            emptyState={
              <Empty className="w-full">
                <EmptyHeader>
                  <EmptyTitle>Опросы через бота отключены</EmptyTitle>
                  <EmptyDescription>
                    Сбор ответов внутри бота больше не используется. Сейчас поддерживается
                    только сценарий с Google Forms.
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => router.push("/polls/settings")}
                  >
                    Настройки формы
                  </Button>
                </EmptyContent>
              </Empty>
            }
            contextMenuActions={{
              getCopyText: (row) =>
                `Ответ #${row.original.id}\nПользователь: ${row.original.user_id}\nDDID: ${row.original.ddid}\nОтвет: ${row.original.answer}`,
            }}
          />
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
