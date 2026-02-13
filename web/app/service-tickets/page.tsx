"use client"

import { useState, useEffect, useCallback } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconPlus, IconClock, IconCheck, IconX, IconAlertTriangle } from "@tabler/icons-react"
import { ServiceTicket, TICKET_STATUS, TICKET_STATUS_LABELS_RU, TICKET_PRIORITY, TICKET_PRIORITY_LABELS_RU } from "@/types"
import { serviceTicketApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, ServerPaginationParams, createSelectColumn } from "@/components/data-table"
import { PageHeader } from "@/components/page-header"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"

export default function ServiceTicketsPage() {
  const router = useRouter()
  const [tickets, setTickets] = useState<ServiceTicket[]>([])
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
      const res = await serviceTicketApi.getPaginated({
        page: serverParams.pageIndex + 1,
        pageSize: serverParams.pageSize,
        search: serverParams.search || undefined,
        sort: serverParams.sort || undefined,
        searchColumns: serverParams.searchColumns?.length ? serverParams.searchColumns : undefined,
      })
      setTickets(res.items)
      setTotal(res.total)
    }).catch((error: any) => {
      toast.error("Не удалось загрузить данные", { description: error.message || "Unknown error" })
      console.error(error)
    })
  }, [serverParams.pageIndex, serverParams.pageSize, serverParams.search, serverParams.sort, serverParams.searchColumns, withLoading])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case TICKET_STATUS.NEW:
        return <Badge variant="outline"><IconX className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.NEW]}</Badge>
      case TICKET_STATUS.ACCEPTED:
        return <Badge variant="outline"><IconClock className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ACCEPTED]}</Badge>
      case TICKET_STATUS.ASSIGNED:
        return <Badge variant="outline"><IconAlertTriangle className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ASSIGNED]}</Badge>
      case TICKET_STATUS.COMPLETED:
        return <Badge variant="outline"><IconCheck className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.COMPLETED]}</Badge>
      default:
        return <Badge variant="outline">Неизвестно</Badge>
    }
  }

  const getPriorityBadge = (priority: number) => {
    switch (priority) {
      case TICKET_PRIORITY.LOW:
        return <Badge variant="outline">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.LOW]}</Badge>
      case TICKET_PRIORITY.MEDIUM:
        return <Badge variant="secondary">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.MEDIUM]}</Badge>
      case TICKET_PRIORITY.HIGH:
        return <Badge variant="destructive">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.HIGH]}</Badge>
      case TICKET_PRIORITY.CRITICAL:
        return <Badge className="bg-red-600 hover:bg-red-700">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.CRITICAL]}</Badge>
      default:
        return <Badge variant="outline">Неопределен</Badge>
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ru-RU", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  const columns: ColumnDef<ServiceTicket>[] = [
    createSelectColumn<ServiceTicket>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: { searchDbColumns: ["id"] },
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "ticket",
      header: "Заявка",
      meta: { searchDbColumns: ["description", "location", "msid"] },
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">{row.original.description || "No description"}</div>
          <div className="text-sm text-muted-foreground">{row.original.location || "No location"}</div>
        </div>
      ),
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
      accessorKey: "object",
      accessorFn: (row) => row.object?.name ?? (row.user?.object_id ? `БЦ-${row.user.object_id}` : ""),
      header: "Объект",
      meta: { searchDbColumns: [] },
      cell: ({ row }) => {
        const obj = row.original.object
        const objectId = obj?.id ?? row.original.user?.object_id
        const display = obj?.name ?? (objectId ? `БЦ-${objectId}` : null)
        if (!display) return <span className="text-muted-foreground">Не назначен</span>
        if (!objectId) return <span className="text-sm">{display}</span>
        return (
          <Link href={`/spaces/${objectId}`} className="text-sm text-primary hover:underline" onClick={(e) => e.stopPropagation()}>
            {display}
          </Link>
        )
      },
    },
    {
      accessorKey: "status",
      header: "Статус",
      meta: { searchDbColumns: ["status"] },
      cell: ({ row }) => getStatusBadge(row.original.status),
    },
    {
      accessorKey: "priority",
      header: "Приоритет",
      meta: { searchDbColumns: ["priority"] },
      cell: ({ row }) => getPriorityBadge(row.original.priority),
    },
    {
      accessorKey: "category",
      header: "Категория",
      meta: { searchDbColumns: ["category"] },
      cell: ({ row }) => <Badge variant="outline">{row.original.category || "No category"}</Badge>,
    },
    {
      accessorKey: "created",
      header: "Создана",
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
          <PageHeader
            title="Заявки на обслуживание"
            description="Управление заявками на техническое обслуживание"
            buttonText={canEdit ? "Создать заявку" : undefined}
            onButtonClick={canEdit ? () => router.push("/service-tickets/edit") : undefined}
            buttonIcon={canEdit ? <IconPlus className="h-4 w-4 mr-2" /> : undefined}
          />

          <DataTable
            data={tickets}
            columns={columns}
            loading={loading}
            loadingMessage="Загрузка заявок..."
            onRowClick={(row) => router.push(`/service-tickets/${row.original.id}`)}
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
