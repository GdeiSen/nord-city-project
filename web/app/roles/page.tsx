"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { toast } from "sonner"
import { IconPlus, IconShield } from "@tabler/icons-react"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Toaster } from "@/components/ui/sonner"
import { roleApi, type RoleResponse } from "@/lib/api"

export default function RolesPage() {
  const [roles, setRoles] = useState<RoleResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    roleApi
      .getAll()
      .then(setRoles)
      .catch((error: any) => toast.error("Не удалось загрузить роли", { description: error?.message }))
      .finally(() => setLoading(false))
  }, [])

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-5 p-4 pt-6 md:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">Роли и права</h1>
              <p className="mt-1 text-sm text-muted-foreground">Классы пользователей и доступ к функциям сайта и бота.</p>
            </div>
            <Button asChild>
              <Link href="/roles/new">
                <IconPlus className="h-4 w-4" />
                Новая роль
              </Link>
            </Button>
          </div>

          {loading ? (
            <div className="text-sm text-muted-foreground">Загрузка...</div>
          ) : (
            <div className="grid gap-3">
              {roles.map((role) => (
                <Link
                  key={role.id}
                  href={`/roles/${role.id}`}
                  className="flex min-w-0 items-center justify-between gap-4 rounded-md border px-4 py-3 transition-colors hover:bg-muted/40"
                >
                  <div className="flex min-w-0 items-start gap-3">
                    <IconShield className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{role.name}</span>
                        <Badge variant="outline">{role.code}</Badge>
                        {role.is_system && <Badge>Системная</Badge>}
                        {role.is_default && <Badge variant="secondary">Everyone</Badge>}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{role.description || "Без описания"}</p>
                    </div>
                  </div>
                  <div className="shrink-0 text-sm text-muted-foreground">{role.permission_ids.length} прав</div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
