"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { IconLink, IconPlus } from "@tabler/icons-react"
import { ColumnDef } from "@tanstack/react-table"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Toaster } from "@/components/ui/sonner"
import { roleApi, type RoleResponse } from "@/lib/api"
import { DataTable, createSelectColumn } from "@/components/data-table"
import { PageHeader } from "@/components/page-header"

const SYSTEM_ROLE_LABELS: Record<string, string> = {
  everyone: "Все пользователи",
  admin: "Администратор",
  super_admin: "Супер администратор",
}

function getRoleName(role: RoleResponse) {
  return SYSTEM_ROLE_LABELS[role.code] ?? role.name
}

export default function RolesPage() {
  const router = useRouter()
  const [roles, setRoles] = useState<RoleResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    roleApi
      .getAll()
      .then(setRoles)
      .catch((error: any) => toast.error("Не удалось загрузить роли", { description: error?.message }))
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnDef<RoleResponse>[] = [
    createSelectColumn<RoleResponse>(),
    {
      accessorKey: "id",
      header: "ID",
      meta: { type: "number", headerLabel: "ID" },
      cell: ({ row }) => <span className="font-medium">#{row.original.id}</span>,
    },
    {
      accessorKey: "name",
      accessorFn: (role) => `${getRoleName(role)} ${role.code}`,
      header: "Роль",
      meta: { type: "string", headerLabel: "Роль" },
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{getRoleName(row.original)}</span>
            <Badge variant="outline">{row.original.code}</Badge>
          </div>
          <div className="text-sm text-muted-foreground">{row.original.description || "Без описания"}</div>
        </div>
      ),
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 pt-6 md:p-8">
          <PageHeader
            title="Роли и права"
            description="Классы пользователей и доступ к функциям сайта и бота"
            actions={
              <div className="flex items-center gap-2">
                <Button variant="outline" asChild>
                  <Link href="/users/role-links">
                    <IconLink className="h-4 w-4" />
                    Ссылки
                  </Link>
                </Button>
                <Button asChild>
                  <Link href="/roles/new">
                    <IconPlus className="h-4 w-4" />
                    Новая роль
                  </Link>
                </Button>
              </div>
            }
          />

          {loading ? (
            <div className="text-sm text-muted-foreground">Загрузка...</div>
          ) : (
            <DataTable
              data={roles}
              columns={columns}
              onRowClick={(row) => router.push(`/roles/${row.original.id}`)}
              contextMenuActions={{
                onEdit: (row) => router.push(`/roles/${row.original.id}`),
                onDelete: async (row) => {
                  if (row.original.is_system) {
                    toast.error("Системную роль нельзя удалить")
                    return
                  }
                  try {
                    await roleApi.delete(row.original.id)
                    setRoles((items) => items.filter((role) => role.id !== row.original.id))
                    toast.success("Роль удалена")
                  } catch (error: any) {
                    toast.error("Не удалось удалить роль", { description: error?.message })
                  }
                },
                getCopyText: (row) => `${getRoleName(row.original)}\n${row.original.code}`,
                deleteTitle: "Удалить роль?",
                deleteDescription: "Это действие нельзя отменить.",
              }}
              emptyState={<span className="text-muted-foreground">Роли не найдены</span>}
            />
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
