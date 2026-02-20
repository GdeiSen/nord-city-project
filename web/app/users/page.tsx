"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Badge } from "@/components/ui/badge"
import { IconUserPlus } from "@tabler/icons-react"
import { User, USER_ROLES, ROLE_LABELS, ROLE_BADGE_VARIANTS } from "@/types"
import { userApi, rentalObjectApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { userColumnMeta } from "@/lib/table-configs"
import { formatDate } from "@/lib/date-utils"
import { PageHeader } from "@/components/page-header"
import {
  useServerPaginatedData,
  useFilterPickerData,
  useCanEdit,
  useIsSuperAdmin,
} from "@/hooks"

export default function UsersPage() {
  const router = useRouter()
  const filterPickerData = useFilterPickerData({ objects: true })
  const canEdit = useCanEdit()
  const canCreateUser = useIsSuperAdmin()
  const {
    data: users,
    total,
    loading,
    serverParams,
    setServerParams,
    refetch,
  } = useServerPaginatedData<User>({
    api: userApi,
    errorMessage: "Не удалось загрузить пользователей",
    initialParams: { sort: "created:desc" },
  })

  const getRoleBadge = (role: number | undefined) => {
    if (role === undefined) return <Badge variant="outline">Неопределен</Badge>
    const roleKey = Object.values(USER_ROLES).find((r) => r === role)
    if (!roleKey) return <Badge variant="outline">Неизвестная роль</Badge>
    return <Badge variant={ROLE_BADGE_VARIANTS[roleKey]}>{ROLE_LABELS[roleKey]}</Badge>
  }

  const columns: ColumnDef<User>[] = [
    createSelectColumn<User>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: userColumnMeta.id,
      cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
    },
    {
      accessorKey: "user",
      accessorFn: (row) => `${row.last_name ?? ""} ${row.first_name ?? ""} ${row.middle_name ?? ""} @${row.username ?? ""}`.trim(),
      header: "Пользователь",
      meta: userColumnMeta.user,
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">
            {row.original.last_name} {row.original.first_name} {row.original.middle_name}
          </div>
          <div className="text-sm text-muted-foreground">@{row.original.username}</div>
        </div>
      ),
    },
    {
      accessorKey: "contacts",
      accessorFn: (row) => `${row.email ?? ""} ${row.phone_number ?? ""}`.trim(),
      header: "Контакты",
      meta: userColumnMeta.contacts,
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="text-sm">{row.original.email}</div>
          <div className="text-sm text-muted-foreground">{row.original.phone_number}</div>
        </div>
      ),
    },
    {
      accessorKey: "role",
      header: "Роль",
      meta: userColumnMeta.role,
      cell: ({ row }) => getRoleBadge(row.original.role),
    },
    {
      accessorKey: "object",
      accessorFn: (row) => row.object?.name ?? (row.object_id ? `БЦ-${row.object_id}` : ""),
      header: "Объект",
      meta: userColumnMeta.object,
      cell: ({ row }) => {
        const obj = row.original.object
        const objectId = row.original.object_id ?? obj?.id
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
      accessorKey: "legal_entity",
      header: "Юр. лицо",
      meta: userColumnMeta.legal_entity,
      cell: ({ row }) => (
        <div className="text-sm">{row.original.legal_entity || <span className="text-muted-foreground">Не указано</span>}</div>
      ),
    },
    {
      accessorKey: "created",
      accessorFn: (row) => new Date(row.created_at).toISOString(),
      header: "Создан",
      meta: userColumnMeta.created,
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
            title="Пользователи"
            description="Управление пользователями системы"
            buttonText={canCreateUser ? "Добавить пользователя" : undefined}
            onButtonClick={canCreateUser ? () => router.push("/users/edit") : undefined}
            buttonIcon={canCreateUser ? <IconUserPlus className="h-4 w-4" /> : undefined}
          />

          <DataTable
            data={users}
            columns={columns}
            filterPickerData={filterPickerData}
            loading={loading}
            loadingMessage="Загрузка пользователей..."
            onRowClick={(row) => router.push(`/users/${row.original.id}`)}
            contextMenuActions={{
              onEdit: (row) => router.push(`/users/edit/${row.original.id}`),
              onDelete: canEdit
                ? async (row) => {
                    try {
                      await userApi.delete(row.original.id)
                      toast.success("Пользователь удалён")
                      refetch()
                    } catch (e: any) {
                      toast.error("Не удалось удалить", { description: e?.message })
                    }
                  }
                : undefined,
              getCopyText: (row) =>
                `${row.original.last_name ?? ""} ${row.original.first_name ?? ""} ${row.original.middle_name ?? ""}\n@${row.original.username ?? ""}\n${row.original.email ?? ""}`.trim(),
              deleteTitle: "Удалить пользователя?",
              deleteDescription: "Это действие нельзя отменить.",
            }}
            serverPagination
            totalRowCount={total}
            serverParams={serverParams}
            onServerParamsChange={setServerParams}
            exportConfig={{
              getExport: (params) => userApi.getExport(params),
              maxLimit: 10_000,
              filename: "users.csv",
            }}
          />
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
