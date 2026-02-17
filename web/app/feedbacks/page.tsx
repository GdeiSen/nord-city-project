"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Feedback } from "@/types"
import { feedbackApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { feedbackColumnMeta } from "@/lib/table-configs"
import { formatDate } from "@/lib/date-utils"
import { PageHeader } from "@/components/page-header"
import {
  useServerPaginatedData,
  useFilterPickerData,
  useCanEdit,
  useIsSuperAdmin,
} from "@/hooks"
import { truncate } from "@/lib/utils"
import { IconPlus } from "@tabler/icons-react"

export default function FeedbacksPage() {
  const router = useRouter()
  const filterPickerData = useFilterPickerData({ users: true })
  const isSuperAdmin = useIsSuperAdmin()
  const {
    data: feedbacks,
    total,
    loading,
    serverParams,
    setServerParams,
    refetch,
  } = useServerPaginatedData<Feedback>({
    api: feedbackApi,
    errorMessage: "Не удалось загрузить данные",
  })
  const canEdit = useCanEdit()

  const columns: ColumnDef<Feedback>[] = [
    createSelectColumn<Feedback>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: feedbackColumnMeta.id,
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "user",
      header: "Пользователь",
      meta: feedbackColumnMeta.user,
      cell: ({ row }) => {
        const u = row.original.user
        const userId = row.original.user_id
        const name = [u?.last_name, u?.first_name, u?.middle_name].filter(Boolean).join(" ").trim()
        const username = u?.username?.trim()
        if (!name && !username) {
          return userId ? (
            <Link href={`/users/${userId}`} className="text-primary hover:underline" onClick={(e) => e.stopPropagation()}>
              ID {userId}
            </Link>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        }
        const content = (
          <div className="space-y-1">
            {name && <div className="font-medium">{name}</div>}
            {username && <div className="text-sm text-muted-foreground">@{username}</div>}
          </div>
        )
        return userId ? (
          <Link href={`/users/${userId}`} className="block text-inherit hover:text-primary hover:underline" onClick={(e) => e.stopPropagation()}>
            {content}
          </Link>
        ) : (
          content
        )
      },
    },
    {
      accessorKey: "feedback",
      header: "Отзыв",
      meta: feedbackColumnMeta.feedback,
      cell: ({ row }) => (
        <div className="space-y-1 max-w-md">
          <div className="text-sm font-medium" title={row.original.answer ?? undefined}>
            {truncate(row.original.answer, 80)}
          </div>
          {row.original.text && (
            <div className="text-xs text-muted-foreground" title={row.original.text}>
              {truncate(row.original.text, 80)}
            </div>
          )}
        </div>
      ),
    },
    {
      accessorKey: "date",
      header: "Дата",
      meta: feedbackColumnMeta.date,
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at, { includeTime: true })}</div>,
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Отзывы пользователей"
            description="Анализ и управление отзывами пользователей"
            buttonText={isSuperAdmin ? "Добавить отзыв" : undefined}
            buttonIcon={isSuperAdmin ? <IconPlus className="h-4 w-4 mr-2" /> : undefined}
            onButtonClick={isSuperAdmin ? () => router.push("/feedbacks/edit") : undefined}
          />

          <DataTable
            data={feedbacks}
            columns={columns}
            filterPickerData={filterPickerData}
            loading={loading}
            loadingMessage="Загрузка отзывов..."
            onRowClick={(row) => router.push(`/feedbacks/${row.original.id}`)}
            contextMenuActions={{
              onEdit: isSuperAdmin ? (row) => router.push(`/feedbacks/edit/${row.original.id}`) : undefined,
              onDelete: canEdit
                ? async (row) => {
                    try {
                      await feedbackApi.delete(row.original.id)
                      toast.success("Отзыв удалён")
                      refetch()
                    } catch (e: any) {
                      toast.error("Не удалось удалить", { description: e?.message })
                    }
                  }
                : undefined,
              getCopyText: (row) => `Отзыв #${row.original.id}\nОтвет: ${row.original.answer ?? ""}\nТекст: ${row.original.text ?? ""}`,
              deleteTitle: "Удалить отзыв?",
              deleteDescription: "Это действие нельзя отменить.",
            }}
            serverPagination
            totalRowCount={total}
            serverParams={serverParams}
            onServerParamsChange={setServerParams}
          />
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
