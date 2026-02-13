"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconUserPlus, IconEdit } from "@tabler/icons-react"
import { User, USER_ROLES, ROLE_LABELS, ROLE_BADGE_VARIANTS } from "@/types"
import { userApi } from "@/lib/api"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef, Row } from "@tanstack/react-table"
import { DataTable, ServerPaginationParams } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
import { PageHeader } from "@/components/page-header"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"
import Link from "next/link"

export default function UsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [serverParams, setServerParams] = useState<ServerPaginationParams>({
    pageIndex: 0,
    pageSize: 10,
    search: "",
    sort: "",
  })
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()

  const fetchUsers = useCallback(async () => {
    await withLoading(async () => {
      const res = await userApi.getPaginated({
        page: serverParams.pageIndex + 1,
        pageSize: serverParams.pageSize,
        search: serverParams.search || undefined,
        sort: serverParams.sort || undefined,
      })
      setUsers(res.items)
      setTotal(res.total)
    }).catch((error: any) => {
      toast.error("Не удалось загрузить пользователей", { description: error.message || "Unknown error" })
      console.error(error)
    })
  }, [serverParams.pageIndex, serverParams.pageSize, serverParams.search, serverParams.sort, withLoading])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const getRoleBadge = (role: number | undefined) => {
    if (role === undefined) return <Badge variant="outline">Неопределен</Badge>
    const roleKey = Object.values(USER_ROLES).find((r) => r === role)
    if (!roleKey) return <Badge variant="outline">Неизвестная роль</Badge>
    return <Badge variant={ROLE_BADGE_VARIANTS[roleKey]}>{ROLE_LABELS[roleKey]}</Badge>
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

  const columns: ColumnDef<User>[] = [
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
      accessorKey: "user",
      accessorFn: (row) => `${row.last_name ?? ""} ${row.first_name ?? ""} ${row.middle_name ?? ""} @${row.username ?? ""}`.trim(),
      header: "Пользователь",
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
      cell: ({ row }) => getRoleBadge(row.original.role),
    },
    {
      accessorKey: "object",
      accessorFn: (row) => (row.object_id ? `БЦ-${row.object_id}` : ""),
      header: "Объект",
      cell: ({ row }) =>
        row.original.object_id ? (
          <Badge variant="outline">БЦ-{row.original.object_id}</Badge>
        ) : (
          <span className="text-muted-foreground">Не назначен</span>
        ),
    },
    {
      accessorKey: "legal_entity",
      header: "Юр. лицо",
      cell: ({ row }) => (
        <div className="text-sm">{row.original.legal_entity || <span className="text-muted-foreground">Не указано</span>}</div>
      ),
    },
    {
      accessorKey: "created",
      accessorFn: (row) => new Date(row.created_at).toISOString(),
      header: "Создан",
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
    ...(canEdit
      ? [
          {
            id: "actions",
            cell: ({ row }: { row: Row<User> }) => (
              <div className="flex items-center justify-end pr-2" onClick={(e) => e.stopPropagation()}>
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/users/edit/${row.original.id}`}>
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
            title="Пользователи"
            description="Управление пользователями системы"
            buttonText={canEdit ? "Добавить пользователя" : undefined}
            onButtonClick={canEdit ? () => router.push("/users/edit") : undefined}
            buttonIcon={canEdit ? <IconUserPlus className="h-4 w-4 mr-2" /> : undefined}
          />

          <DataTable
            data={users}
            columns={columns}
            loading={loading}
            loadingMessage="Загрузка пользователей..."
            onRowClick={(row) => router.push(`/users/${row.original.id}`)}
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
