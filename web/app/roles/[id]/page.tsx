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

  const groupedPermissions = useMemo(() => {
    const groups = new Map<string, PermissionResponse[]>()
    for (const permission of permissions) {
      groups.set(permission.scope, [...(groups.get(permission.scope) ?? []), permission])
    }
    return Array.from(groups.entries()).sort(([left], [right]) => left.localeCompare(right))
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
              <h1 className="text-2xl font-semibold">{isNew ? "Новая роль" : role.name || "Роль"}</h1>
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

          <div className="grid max-w-5xl gap-4 md:grid-cols-2">
            {groupedPermissions.map(([scope, items]) => (
              <div key={scope} className="rounded-md border p-4">
                <h2 className="font-medium">{scope}</h2>
                <div className="mt-3 grid gap-3">
                  {items.map((permission) => (
                    <label key={permission.id} className="flex items-start gap-3 text-sm">
                      <Checkbox
                        checked={selectedIds.has(permission.id)}
                        onCheckedChange={(checked) => togglePermission(permission.id, checked === true)}
                      />
                      <span>
                        <span className="block font-medium">{permission.name}</span>
                        <span className="block text-muted-foreground">{permission.code}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
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
