"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { IconEdit } from "@tabler/icons-react"
import { Feedback } from "@/types"
import { feedbackApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef, Row } from "@tanstack/react-table"
import { DataTable, ServerPaginationParams } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
import { PageHeader } from "@/components/page-header"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"
import Link from "next/link"

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
  const canEdit = useCanEdit()

  const fetchData = useCallback(async () => {
    await withLoading(async () => {
      const res = await feedbackApi.getPaginated({
        page: serverParams.pageIndex + 1,
        pageSize: serverParams.pageSize,
        search: serverParams.search || undefined,
        sort: serverParams.sort || undefined,
      })
      setFeedbacks(res.items)
      setTotal(res.total)
    }).catch((error: any) => {
      toast.error("Не удалось загрузить данные")
      console.error(error)
    })
  }, [serverParams.pageIndex, serverParams.pageSize, serverParams.search, serverParams.sort, withLoading])

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
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        />
      ),
      cell: ({ row }) => (
        <Checkbox checked={row.getIsSelected()} onCheckedChange={(value) => row.toggleSelected(!!value)} />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    {
      accessorKey: "id",
      header: "ID",
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "user",
      header: "Пользователь",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">
            {row.original.user?.last_name ?? ""} {row.original.user?.first_name ?? ""}
          </div>
          <div className="text-sm text-muted-foreground">@{row.original.user?.username}</div>
        </div>
      ),
    },
    {
      accessorKey: "feedback",
      header: "Отзыв",
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
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
    ...(canEdit
      ? [
          {
            id: "actions",
            cell: ({ row }: { row: Row<Feedback> }) => (
              <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/feedbacks/edit/${row.original.id}`}>
                    <IconEdit className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ),
          },
        ]
      : []),
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
