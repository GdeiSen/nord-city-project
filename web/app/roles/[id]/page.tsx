"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Toaster } from "@/components/ui/sonner"
import { roleApi, type PermissionResponse, type RoleResponse } from "@/lib/api"

const SYSTEM_ROLE_LABELS: Record<string, string> = {
  everyone: "Все пользователи",
  admin: "Администратор",
  super_admin: "Супер администратор",
}

const PERMISSION_SCOPE_LABELS: Record<string, string> = {
  site: "Сайт",
  roles: "Роли",
  users: "Пользователи",
  localization: "Локализация",
  notifications: "Оповещения",
  bot: "Бот",
  service_tickets: "Заявки на обслуживание",
  parking: "Парковка",
}

function getRoleName(role: Partial<RoleResponse>) {
  const code = role.code ?? ""
  return SYSTEM_ROLE_LABELS[code] ?? role.name ?? "Роль"
}

function getPermissionScopeLabel(scope: string) {
  return PERMISSION_SCOPE_LABELS[scope] ?? scope
}

export default function RoleDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const isNew = params.id === "new"
  const roleId = Number(params.id)

  const [permissions, setPermissions] = useState<PermissionResponse[]>([])
  const [role, setRole] = useState<Partial<RoleResponse>>({ permission_ids: [] })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      roleApi.getPermissions(),
      isNew ? Promise.resolve(null) : roleApi.getById(roleId),
    ])
      .then(([permissionItems, roleItem]) => {
        setPermissions(permissionItems)
        if (roleItem) setRole(roleItem)
      })
      .catch((error: any) => {
        toast.error("Не удалось загрузить роль", { description: error?.message })
        router.push("/roles")
      })
  }, [isNew, roleId, router])

  const sortedPermissions = useMemo(() => {
    return [...permissions].sort((left, right) => {
      const leftScope = getPermissionScopeLabel(left.scope)
      const rightScope = getPermissionScopeLabel(right.scope)
      return leftScope.localeCompare(rightScope, "ru") || left.name.localeCompare(right.name, "ru")
    })
  }, [permissions])

  const selectedIds = new Set(role.permission_ids ?? [])

  const togglePermission = (permissionId: number, checked: boolean) => {
    setRole((current) => {
      const currentIds = new Set(current.permission_ids ?? [])
      if (checked) currentIds.add(permissionId)
      else currentIds.delete(permissionId)
      return { ...current, permission_ids: Array.from(currentIds).sort((a, b) => a - b) }
    })
  }

  const save = async () => {
    if (!role.name?.trim() || !role.code?.trim()) {
      toast.error("Укажите код и название роли")
      return
    }
    setSaving(true)
    try {
      const payload = {
        code: role.code.trim(),
        name: role.name.trim(),
        description: role.description?.trim() || undefined,
        permission_ids: role.permission_ids ?? [],
      }
      const saved = isNew ? await roleApi.create(payload) : (await roleApi.update(roleId, payload), { id: roleId })
      toast.success("Роль сохранена")
      router.push(`/roles/${saved.id}`)
    } catch (error: any) {
      toast.error("Не удалось сохранить роль", { description: error?.message })
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-5 p-4 pt-6 md:p-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold">{isNew ? "Новая роль" : getRoleName(role)}</h1>
              <p className="mt-1 text-sm text-muted-foreground">Настройка прав доступа для класса пользователей.</p>
            </div>
            <Button variant="outline" asChild>
              <Link href="/roles">К списку</Link>
            </Button>
          </div>

          <div className="grid max-w-3xl gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="code">Код</Label>
                <Input
                  id="code"
                  value={role.code ?? ""}
                  disabled={!isNew && role.is_system}
                  onChange={(event) => setRole((current) => ({ ...current, code: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Название</Label>
                <Input
                  id="name"
                  value={role.name ?? ""}
                  onChange={(event) => setRole((current) => ({ ...current, name: event.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Описание</Label>
              <Textarea
                id="description"
                value={role.description ?? ""}
                onChange={(event) => setRole((current) => ({ ...current, description: event.target.value }))}
              />
            </div>
          </div>

          <div className="max-w-5xl rounded-md border">
            <div className="grid grid-cols-[minmax(0,1fr)_42px] gap-3 border-b bg-muted/40 px-4 py-2 text-sm font-medium text-muted-foreground sm:grid-cols-[minmax(0,1fr)_180px_42px]">
              <span>Право</span>
              <span className="hidden sm:block">Раздел</span>
              <span className="text-right">Вкл.</span>
            </div>
            <div className="divide-y">
              {sortedPermissions.map((permission) => (
                <label
                  key={permission.id}
                  className="grid cursor-pointer grid-cols-[minmax(0,1fr)_42px] items-center gap-3 px-4 py-3 text-sm hover:bg-muted/30 sm:grid-cols-[minmax(0,1fr)_180px_42px]"
                >
                  <span className="min-w-0">
                    <span className="block font-medium">{permission.name}</span>
                    <span className="block truncate text-muted-foreground">{permission.code}</span>
                    <span className="block text-muted-foreground sm:hidden">{getPermissionScopeLabel(permission.scope)}</span>
                  </span>
                  <span className="hidden text-muted-foreground sm:block">{getPermissionScopeLabel(permission.scope)}</span>
                  <span className="flex justify-end">
                    <Checkbox
                      checked={selectedIds.has(permission.id)}
                      onCheckedChange={(checked) => togglePermission(permission.id, checked === true)}
                    />
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={save} disabled={saving}>
              {saving ? "Сохранение..." : "Сохранить"}
            </Button>
          </div>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
