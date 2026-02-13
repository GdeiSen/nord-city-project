"use client"

import { useState, useEffect, useCallback } from "react"
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
import { DataTable, ServerPaginationParams, createSelectColumn } from "@/components/data-table"
import { PageHeader } from "@/components/page-header"
import { useLoading } from "@/hooks/use-loading"
export default function FeedbacksPage() {
  const router = useRouter()
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([])
  const [total, setTotal] = useState(0)
  const [serverParams, setServerParams] = useState<ServerPaginationParams>({
    pageIndex: 0,
    pageSize: 10,
    search: "",
    sort: "",
  })
  const { loading, withLoading } = useLoading(true)

  const fetchData = useCallback(async () => {
    await withLoading(async () => {
      const res = await feedbackApi.getPaginated({
        page: serverParams.pageIndex + 1,
        pageSize: serverParams.pageSize,
        search: serverParams.search || undefined,
        sort: serverParams.sort || undefined,
        searchColumns: serverParams.searchColumns?.length ? serverParams.searchColumns : undefined,
      })
      setFeedbacks(res.items)
      setTotal(res.total)
    }).catch((error: any) => {
      toast.error("Не удалось загрузить данные")
      console.error(error)
    })
  }, [serverParams.pageIndex, serverParams.pageSize, serverParams.search, serverParams.sort, serverParams.searchColumns, withLoading])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString("ru-RU", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })

  const columns: ColumnDef<Feedback>[] = [
    createSelectColumn<Feedback>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: { searchDbColumns: ["id"] },
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "user",
      header: "Пользователь",
      meta: { searchDbColumns: [] },
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
      meta: { searchDbColumns: ["answer", "ddid"] },
      cell: ({ row }) => (
        <div className="space-y-1 max-w-md">
          <div className="text-sm font-medium line-clamp-2">{row.original.answer}</div>
          {row.original.text && <div className="text-xs text-muted-foreground line-clamp-1">{row.original.text}</div>}
        </div>
      ),
    },
    {
      accessorKey: "date",
      header: "Дата",
      meta: { searchDbColumns: ["created_at"] },
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader title="Отзывы пользователей" description="Анализ и управление отзывами пользователей" />

          <DataTable
            data={feedbacks}
            columns={columns}
            loading={loading}
            loadingMessage="Загрузка отзывов..."
            onRowClick={(row) => router.push(`/feedbacks/${row.original.id}`)}
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
