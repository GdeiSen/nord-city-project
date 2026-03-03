"use client"

import Link from "next/link"
import { ColumnDef } from "@tanstack/react-table"

import { AppSidebar } from "@/components/app-sidebar"
import { DataTable } from "@/components/data-table"
import { MarqueeText } from "@/components/marquee-text"
import { PageHeader } from "@/components/page-header"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { useServerPaginatedData } from "@/hooks"
import { formatDate } from "@/lib/date-utils"
import { storageFileApi } from "@/lib/api"
import { storageFileColumnMeta } from "@/lib/table-configs"
import { StorageFile } from "@/types"

function getEntityDetailUrl(entityType?: string, entityId?: number): string | null {
  if (!entityType || entityId == null) {
    return null
  }

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
    case "Space":
      return `/spaces/${entityId}`
    default:
      return null
  }
}

function getEntityLabel(entityType?: string, entityId?: number): string {
  if (!entityType || entityId == null) {
    return "Не привязан"
  }

  return `${entityType} #${entityId}`
}

export default function FileStoragePage() {
  const {
    data,
    total,
    loading,
    serverParams,
    setServerParams,
  } = useServerPaginatedData<StorageFile>({
    api: storageFileApi,
    errorMessage: "Не удалось загрузить файлы",
    initialParams: { sort: "created_at:desc" },
  })

  const columns: ColumnDef<StorageFile>[] = [
    {
      accessorKey: "id",
      header: "ID",
      meta: storageFileColumnMeta.id,
      cell: ({ row }) => <span className="font-medium">#{row.original.id}</span>,
    },
    {
      accessorKey: "original_name",
      header: "Файл",
      meta: storageFileColumnMeta.original_name,
      cell: ({ row }) => (
        <div className="space-y-1">
          <a
            href={row.original.public_url}
            target="_blank"
            rel="noreferrer"
            className="block text-primary hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            <MarqueeText
              text={row.original.original_name}
              textClassName="font-medium"
              maxWidthPx={320}
            />
          </a>
          <MarqueeText
            text={row.original.storage_path}
            textClassName="text-xs text-muted-foreground"
            maxWidthPx={420}
          />
        </div>
      ),
    },
    {
      accessorKey: "kind",
      header: "Тип",
      meta: storageFileColumnMeta.kind,
    },
    {
      accessorKey: "category",
      header: "Категория",
      meta: storageFileColumnMeta.category,
    },
    {
      accessorKey: "entity_type",
      header: "Сущность",
      meta: storageFileColumnMeta.entity_type,
      cell: ({ row }) => {
        const label = getEntityLabel(row.original.entity_type, row.original.entity_id)
        const url = getEntityDetailUrl(row.original.entity_type, row.original.entity_id)

        if (!row.original.entity_type || row.original.entity_id == null) {
          return <span className="text-muted-foreground">Не привязан</span>
        }
        if (!url) {
          return <MarqueeText text={label} maxWidthPx={220} />
        }

        return (
          <Link
            href={url}
            className="block text-primary hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            <MarqueeText text={label} maxWidthPx={220} />
          </Link>
        )
      },
    },
    {
      accessorKey: "content_type",
      header: "MIME",
      meta: storageFileColumnMeta.content_type,
      cell: ({ row }) => (
        <MarqueeText
          text={row.original.content_type || row.original.extension || "—"}
          maxWidthPx={320}
        />
      ),
    },
    {
      accessorKey: "created_at",
      header: "Создан",
      meta: storageFileColumnMeta.created_at,
      cell: ({ row }) => formatDate(row.original.created_at, { includeTime: true }),
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Хранилище файлов"
            description="Системный реестр файлов, загруженных через storage layer."
          />

          <DataTable
            data={data}
            columns={columns}
            loading={loading}
            loadingMessage="Загрузка файлов..."
            serverPagination
            totalRowCount={total}
            serverParams={serverParams}
            onServerParamsChange={setServerParams}
          />
        </div>
      </SidebarInset>
    </>
  )
}
