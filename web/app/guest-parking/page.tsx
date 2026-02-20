"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { IconPlus } from "@tabler/icons-react"
import { GuestParkingRequest } from "@/types"
import { guestParkingApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { guestParkingColumnMeta } from "@/lib/table-configs/guest-parking"
import { formatDate } from "@/lib/date-utils"
import { PageHeader } from "@/components/page-header"
import {
  useServerPaginatedData,
  useFilterPickerData,
  useCanEdit,
} from "@/hooks"

/** Заявка в течение 15 минут — подсветка синим полупрозрачным */
function isWithin15Minutes(arrivalDate: string | undefined): boolean {
  if (!arrivalDate) return false
  const now = new Date()
  const arrival = new Date(arrivalDate)
  const diffMs = arrival.getTime() - now.getTime()
  const diffMins = diffMs / (1000 * 60)
  return diffMins > 0 && diffMins <= 15
}

export default function GuestParkingPage() {
  const router = useRouter()
  const filterPickerData = useFilterPickerData({ users: true })
  const {
    data: requests,
    total,
    loading,
    serverParams,
    setServerParams,
    refetch,
  } = useServerPaginatedData<GuestParkingRequest>({
    api: guestParkingApi,
    errorMessage: "Не удалось загрузить данные",
    initialParams: { sort: "arrival:desc" },
  })
  const canEdit = useCanEdit()

  const columns: ColumnDef<GuestParkingRequest>[] = [
    createSelectColumn<GuestParkingRequest>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: guestParkingColumnMeta.id,
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "arrival",
      header: "Дата и время заезда",
      meta: guestParkingColumnMeta.arrival,
      accessorFn: (row) => row.arrival_date,
      cell: ({ row }) => (
        <div className="text-sm">
          {formatDate(row.original.arrival_date, { includeTime: true })}
        </div>
      ),
    },
    {
      accessorKey: "license_plate",
      header: "Госномер",
      meta: guestParkingColumnMeta.license_plate,
      cell: ({ row }) => <div className="font-medium">{row.original.license_plate}</div>,
    },
    {
      accessorKey: "car_make_color",
      header: "Марка и цвет",
      meta: guestParkingColumnMeta.car_make_color,
    },
    {
      accessorKey: "driver_phone",
      header: "Телефон водителя",
      meta: guestParkingColumnMeta.driver_phone,
    },
    {
      accessorKey: "user",
      header: "Арендатор",
      meta: guestParkingColumnMeta.user,
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
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Заявки на гостевую парковку"
            description="Управление заявками на гостевые парковочные места"
            buttonText={canEdit ? "Создать заявку" : undefined}
            onButtonClick={canEdit ? () => router.push("/guest-parking/edit") : undefined}
            buttonIcon={canEdit ? <IconPlus className="h-4 w-4" /> : undefined}
          />

          <DataTable
            data={requests}
            columns={columns}
            filterPickerData={filterPickerData}
            loading={loading}
            loadingMessage="Загрузка заявок..."
            onRowClick={(row) => router.push(`/guest-parking/${row.original.id}`)}
            getRowClassName={(row) =>
              isWithin15Minutes(row.original.arrival_date) ? "bg-blue-500/10" : undefined
            }
            contextMenuActions={{
              onEdit: (row) => router.push(`/guest-parking/edit/${row.original.id}`),
              onDelete: canEdit
                ? async (row) => {
                    try {
                      await guestParkingApi.delete(row.original.id)
                      toast.success("Заявка удалена")
                      refetch()
                    } catch (e: any) {
                      toast.error("Не удалось удалить", { description: e?.message })
                    }
                  }
                : undefined,
              getCopyText: (row) =>
                `Заявка #${row.original.id}\nЗаезд: ${row.original.arrival_date}\nГосномер: ${row.original.license_plate}`,
              deleteTitle: "Удалить заявку?",
              deleteDescription: "Это действие нельзя отменить. Сообщение в чате администраторов будет удалено.",
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
