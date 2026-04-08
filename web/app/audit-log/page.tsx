"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { AuditEntrySheet } from "@/components/audit-entry-sheet"
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
import type { AuditLogEntry } from "@/types"

const ENTITY_TYPE_LABELS: Record<string, string> = {
  ServiceTicket: "Заявка",
  GuestParkingRequest: "Гостевая парковка",
  User: "Пользователь",
  Feedback: "Отзыв",
  Object: "Объект",
  Space: "Помещение",
  SpaceView: "Просмотр",
  PollAnswer: "Опрос",
  GuestParkingSettings: "Настройки парковки",
  StorageFile: "Файл",
}

/** URL списка (таблицы) сущностей по типу */
function getEntityListUrl(entityType: string): string | null {
  switch (entityType) {
    case "ServiceTicket":
      return "/service-tickets"
    case "GuestParkingRequest":
      return "/guest-parking"
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
    case "StorageFile":
      return "/file-storage"
    default:
      return null
  }
}

function renderActor(entry: AuditLogEntry, stopPropagation: boolean = true) {
  const actor = entry.actor
  const label = actor?.label ?? entry.actor_display ?? entry.source_service ?? "—"
  if (actor?.href) {
    return (
      <Link
        href={actor.href}
        className="text-primary hover:underline"
        onClick={stopPropagation ? (e) => e.stopPropagation() : undefined}
      >
        {label}
      </Link>
    )
  }
  return <span className="text-sm text-muted-foreground">{label}</span>
}

function getEntityDetailUrl(entityType: string, entityId: number): string | null {
  switch (entityType) {
    case "ServiceTicket":
      return `/service-tickets/${entityId}`
    case "GuestParkingRequest":
      return `/guest-parking/${entityId}`
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
  const searchParams = useSearchParams()
  const filterPickerData = useFilterPickerData({})
  const {
    data: entries,
    total,
    loading,
    serverParams,
    setServerParams,
  } = useServerPaginatedData<AuditLogEntry>({
    api: auditLogApi,
    errorMessage: "Не удалось загрузить журнал аудита",
    initialParams: { sort: "created:desc" },
  })
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null)
  const [isEntrySheetOpen, setIsEntrySheetOpen] = useState(false)

  useEffect(() => {
    const rawEntryId = searchParams.get("entryId")
    if (!rawEntryId) return
    const entryId = Number(rawEntryId)
    if (!Number.isFinite(entryId)) return

    auditLogApi.getById(entryId)
      .then((entry) => {
        setSelectedEntry(entry)
        setIsEntrySheetOpen(true)
      })
      .catch(() => {})
  }, [searchParams])

  const columns: ColumnDef<AuditLogEntry>[] = [
    createSelectColumn<AuditLogEntry>(),
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
            {action}
          </Badge>
        )
      },
    },
    {
      accessorKey: "actor_display",
      header: "Кто изменил",
      meta: auditLogColumnMeta.actor_display,
      cell: ({ row }) => renderActor(row.original),
    },
    {
      accessorKey: "source_service",
      header: "Источник",
      meta: auditLogColumnMeta.source_service,
      cell: ({ row }) => (
        <span className="text-sm text-muted-foreground">
          {row.original.source_service ?? "—"}
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
              setSelectedEntry(row.original)
              setIsEntrySheetOpen(true)
            }}
            contextMenuActions={{
              getCopyText: (row) =>
                `#${row.original.id} ${row.original.entity_type} #${row.original.entity_id} ${row.original.action} ${row.original.actor?.label ?? row.original.actor_display ?? ""} ${row.original.created_at ?? ""}`,
            }}
            serverPagination
            totalRowCount={total}
            serverParams={serverParams}
            onServerParamsChange={setServerParams}
          />
        </div>
      </SidebarInset>
      <AuditEntrySheet
        entry={selectedEntry}
        open={isEntrySheetOpen}
        onOpenChange={(open) => {
          setIsEntrySheetOpen(open)
          if (!open) {
            setSelectedEntry(null)
          }
        }}
      />
      <Toaster />
    </>
  )
}
