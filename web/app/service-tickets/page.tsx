"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconPlus, IconEdit, IconClock, IconCheck, IconX, IconAlertTriangle } from "@tabler/icons-react"
import { ServiceTicket, TICKET_STATUS, TICKET_STATUS_LABELS_RU, TICKET_PRIORITY, TICKET_PRIORITY_LABELS_RU } from "@/types"
import { serviceTicketApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef, Row } from "@tanstack/react-table"
import { DataTable, ServerPaginationParams } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
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
      })
      setTickets(res.items)
      setTotal(res.total)
    }).catch((error: any) => {
      toast.error("Не удалось загрузить данные", { description: error.message || "Unknown error" })
      console.error(error)
    })
  }, [serverParams.pageIndex, serverParams.pageSize, serverParams.search, serverParams.sort, withLoading])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const getStatusBadge = (status: string) => {
    switch (status) {
      case TICKET_STATUS.NEW:
        return <Badge variant="destructive"><IconX className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.NEW]}</Badge>
      case TICKET_STATUS.ACCEPTED:
        return <Badge variant="secondary"><IconClock className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ACCEPTED]}</Badge>
      case TICKET_STATUS.ASSIGNED:
        return <Badge variant="default"><IconAlertTriangle className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ASSIGNED]}</Badge>
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
    {
      id: "select",
      header: ({ table }) => (
        <div className="flex items-center justify-center">
          <Checkbox
            checked={
              table.getIsAllPageRowsSelected() ||
              (table.getIsSomePageRowsSelected() && "indeterminate")
            }
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
            aria-label="Select all"
          />
        </div>
      ),
      cell: ({ row }) => (
        <div className="flex items-center justify-center">
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        </div>
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
      accessorKey: "ticket",
      header: "Заявка",
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
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">
            {row.original.user?.last_name} {row.original.user?.first_name}
          </div>
          <div className="text-sm text-muted-foreground">@{row.original.user?.username}</div>
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Статус",
      cell: ({ row }) => getStatusBadge(row.original.status),
    },
    {
      accessorKey: "priority",
      header: "Приоритет",
      cell: ({ row }) => getPriorityBadge(row.original.priority),
    },
    {
      accessorKey: "category",
      header: "Категория",
      cell: ({ row }) => <Badge variant="outline">{row.original.category || "No category"}</Badge>,
    },
    {
      accessorKey: "created",
      header: "Создана",
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
    ...(canEdit
      ? [
          {
            id: "actions",
            cell: ({ row }: { row: Row<ServiceTicket> }) => (
              <div className="flex items-center justify-end pr-2" onClick={(e) => e.stopPropagation()}>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/service-tickets/edit/${row.original.id}`}>
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
