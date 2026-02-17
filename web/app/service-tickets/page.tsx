"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconPlus } from "@tabler/icons-react"
import { ServiceTicket, TICKET_STATUS, TICKET_STATUS_LABELS_RU } from "@/types"
import { serviceTicketApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { serviceTicketColumnMeta } from "@/lib/table-configs"
import { formatDate } from "@/lib/date-utils"
import { PageHeader } from "@/components/page-header"
import {
  useServerPaginatedData,
  useFilterPickerData,
  useCanEdit,
} from "@/hooks"

export default function ServiceTicketsPage() {
  const router = useRouter()
  const filterPickerData = useFilterPickerData({ users: true, objects: true })
  const {
    data: tickets,
    total,
    loading,
    serverParams,
    setServerParams,
    refetch,
  } = useServerPaginatedData<ServiceTicket>({
    api: serviceTicketApi,
    errorMessage: "Не удалось загрузить данные",
  })
  const canEdit = useCanEdit()

  const getStatusBadge = (status: string) => {
    const label = TICKET_STATUS_LABELS_RU[status as keyof typeof TICKET_STATUS_LABELS_RU] ?? status ?? "—"
    const colorClass =
      status === TICKET_STATUS.NEW
        ? "bg-blue-500 text-white border-blue-500 hover:bg-blue-500"
        : status === TICKET_STATUS.ASSIGNED
          ? "bg-gray-500 text-white border-gray-500 hover:bg-gray-500"
          : status === TICKET_STATUS.IN_PROGRESS || status === TICKET_STATUS.ACCEPTED
            ? "bg-orange-500 text-white border-orange-500 hover:bg-orange-500"
            : status === TICKET_STATUS.COMPLETED
              ? "bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-600"
              : ""
    return <Badge variant="outline" className={colorClass || undefined}>{label}</Badge>
  }

  const columns: ColumnDef<ServiceTicket>[] = [
    createSelectColumn<ServiceTicket>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: serviceTicketColumnMeta.id,
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "ticket",
      header: "Заявка",
      meta: serviceTicketColumnMeta.ticket,
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
      meta: serviceTicketColumnMeta.user,
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
      accessorFn: (row) => row.object?.name ?? (row.object_id ?? row.user?.object_id ? `БЦ-${row.object_id ?? row.user?.object_id}` : ""),
      header: "Объект",
      meta: serviceTicketColumnMeta.object,
      cell: ({ row }) => {
        const obj = row.original.object
        const objectId = obj?.id ?? row.original.object_id ?? row.original.user?.object_id
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
      meta: serviceTicketColumnMeta.status,
      cell: ({ row }) => getStatusBadge(row.original.status),
    },
    {
      accessorKey: "created",
      header: "Создана",
      meta: serviceTicketColumnMeta.created,
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
            title="Заявки на обслуживание"
            description="Управление заявками на техническое обслуживание"
            buttonText={canEdit ? "Создать заявку" : undefined}
            onButtonClick={canEdit ? () => router.push("/service-tickets/edit") : undefined}
            buttonIcon={canEdit ? <IconPlus className="h-4 w-4" /> : undefined}
          />

          <DataTable
            data={tickets}
            columns={columns}
            filterPickerData={filterPickerData}
            loading={loading}
            loadingMessage="Загрузка заявок..."
            onRowClick={(row) => router.push(`/service-tickets/${row.original.id}`)}
            exportConfig={{
              getExport: (params) => serviceTicketApi.getExport(params),
              maxLimit: 10_000,
              filename: "service-tickets.csv",
            }}
            contextMenuActions={{
              onEdit: (row) => router.push(`/service-tickets/edit/${row.original.id}`),
              onDelete: canEdit
                ? async (row) => {
                    try {
                      await serviceTicketApi.delete(row.original.id)
                      toast.success("Заявка удалена")
                      refetch()
                    } catch (e: any) {
                      toast.error("Не удалось удалить", { description: e?.message })
                    }
                  }
                : undefined,
              getCopyText: (row) =>
                `Заявка #${row.original.id}\nСтатус: ${row.original.status}\nОписание: ${row.original.description ?? ""}`,
              deleteTitle: "Удалить заявку?",
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
