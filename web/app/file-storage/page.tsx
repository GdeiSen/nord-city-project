"use client"

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
            className="block truncate font-medium text-primary hover:underline"
            onClick={(event) => event.stopPropagation()}
          >
            {row.original.original_name}
          </a>
          <MarqueeText
            text={row.original.storage_path}
            textClassName="text-xs text-muted-foreground"
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
        if (!row.original.entity_type || row.original.entity_id == null) {
          return <span className="text-muted-foreground">Не привязан</span>
        }
        return `${row.original.entity_type} #${row.original.entity_id}`
      },
    },
    {
      accessorKey: "content_type",
      header: "MIME",
      meta: storageFileColumnMeta.content_type,
      cell: ({ row }) => row.original.content_type || row.original.extension || "—",
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
