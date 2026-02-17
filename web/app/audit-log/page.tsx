"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"
import { auditLogColumnMeta } from "@/lib/table-configs"
import { formatDate } from "@/lib/date-utils"
import { auditLogApi } from "@/lib/api"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { PageHeader } from "@/components/page-header"
import { useServerPaginatedData, useFilterPickerData } from "@/hooks"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"

const ENTITY_TYPE_LABELS: Record<string, string> = {
  ServiceTicket: "Заявка",
  User: "Пользователь",
  Feedback: "Отзыв",
  Object: "Объект",
  Space: "Помещение",
  SpaceView: "Просмотр",
  PollAnswer: "Опрос",
}

const ACTION_LABELS: Record<string, string> = {
  create: "Создание",
  update: "Изменение",
  delete: "Удаление",
}

/** URL списка (таблицы) сущностей по типу */
function getEntityListUrl(entityType: string): string | null {
  switch (entityType) {
    case "ServiceTicket":
      return "/service-tickets"
    case "User":
      return "/users"
    case "Feedback":
      return "/feedbacks"
    case "Object":
    case "Space":
    case "SpaceView":
      return "/spaces"
    case "PollAnswer":
      return "/spaces"
    default:
      return null
  }
}

function getEntityDetailUrl(entityType: string, entityId: number): string | null {
  switch (entityType) {
    case "ServiceTicket":
      return `/service-tickets/${entityId}`
    case "User":
      return `/users/${entityId}`
    case "Feedback":
      return `/feedbacks/${entityId}`
    case "Object":
      return `/spaces/${entityId}`
    case "Space":
      return `/spaces/${entityId}`
    default:
      return null
  }
}

export default function AuditLogPage() {
  const router = useRouter()
  const filterPickerData = useFilterPickerData({})
  const {
    data: entries,
    total,
    loading,
    serverParams,
    setServerParams,
    refetch,
  } = useServerPaginatedData<any>({
    api: auditLogApi,
    errorMessage: "Не удалось загрузить журнал аудита",
  })

  const columns: ColumnDef<any>[] = [
    createSelectColumn<any>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: auditLogColumnMeta.id,
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "entity_type",
      header: "Тип сущности",
      meta: auditLogColumnMeta.entity_type,
      cell: ({ row }) => {
        const type = row.original.entity_type
        const label = ENTITY_TYPE_LABELS[type] ?? type
        const listUrl = getEntityListUrl(type)
        return listUrl ? (
          <Link
            href={listUrl}
            className="text-primary hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {label}
          </Link>
        ) : (
          <span>{label}</span>
        )
      },
    },
    {
      accessorKey: "entity_id",
      header: "ID сущности",
      meta: auditLogColumnMeta.entity_id,
      cell: ({ row }) => {
        const url = getEntityDetailUrl(row.original.entity_type, row.original.entity_id)
        const id = row.original.entity_id
        return url ? (
          <Link
            href={url}
            className="text-primary hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            #{id}
          </Link>
        ) : (
          <span>#{id}</span>
        )
      },
    },
    {
      accessorKey: "action",
      header: "Действие",
      meta: auditLogColumnMeta.action,
      cell: ({ row }) => {
        const action = row.original.action
        const variant =
          action === "create"
            ? "default"
            : action === "delete"
              ? "destructive"
              : "secondary"
        return (
          <Badge variant={variant}>
            {ACTION_LABELS[action] ?? action}
          </Badge>
        )
      },
    },
    {
      accessorKey: "assignee_display",
      header: "Исполнитель",
      meta: auditLogColumnMeta.assignee_display,
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.assignee_display ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "created",
      accessorFn: (row) => row.created_at,
      header: "Дата",
      meta: auditLogColumnMeta.created,
      cell: ({ row }) => (
        <div className="text-sm">
          {formatDate(row.original.created_at, { includeTime: true })}
        </div>
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
            title="Журнал аудита"
            description="История всех изменений в системе"
          />

          <DataTable
            data={entries}
            columns={columns}
            filterPickerData={filterPickerData}
            loading={loading}
            loadingMessage="Загрузка журнала аудита..."
            onRowClick={(row) => {
              const url = getEntityDetailUrl(row.original.entity_type, row.original.entity_id)
              if (url) router.push(url)
            }}
            contextMenuActions={{
              getCopyText: (row) =>
                `#${row.original.id} ${row.original.entity_type} #${row.original.entity_id} ${row.original.action} ${row.original.assignee_display ?? ""} ${row.original.created_at ?? ""}`,
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
