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
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

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

function slugifyRoleCode(value: string) {
  const translit: Record<string, string> = {
    а: "a",
    б: "b",
    в: "v",
    г: "g",
    д: "d",
    е: "e",
    ё: "e",
    ж: "zh",
    з: "z",
    и: "i",
    й: "y",
    к: "k",
    л: "l",
    м: "m",
    н: "n",
    о: "o",
    п: "p",
    р: "r",
    с: "s",
    т: "t",
    у: "u",
    ф: "f",
    х: "h",
    ц: "c",
    ч: "ch",
    ш: "sh",
    щ: "sch",
    ъ: "",
    ы: "y",
    ь: "",
    э: "e",
    ю: "yu",
    я: "ya",
  }
  const transliterated = value
    .trim()
    .toLowerCase()
    .split("")
    .map((char) => translit[char] ?? char)
    .join("")
  return transliterated
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_{2,}/g, "_")
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

  const groupedPermissions = useMemo(() => {
    const sorted = [...permissions].sort((left, right) => {
      const leftScope = getPermissionScopeLabel(left.scope)
      const rightScope = getPermissionScopeLabel(right.scope)
      return leftScope.localeCompare(rightScope, "ru") || left.name.localeCompare(right.name, "ru")
    })
    const groups = new Map<string, PermissionResponse[]>()
    for (const permission of sorted) {
      const scope = getPermissionScopeLabel(permission.scope)
      groups.set(scope, [...(groups.get(scope) ?? []), permission])
    }
    return Array.from(groups.entries())
  }, [permissions])

  const selectedIds = new Set(role.permission_ids ?? [])
  const generatedRoleCode = isNew ? slugifyRoleCode(role.name ?? "") : role.code ?? ""

  const togglePermission = (permissionId: number, checked: boolean) => {
    setRole((current) => {
      const currentIds = new Set(current.permission_ids ?? [])
      if (checked) currentIds.add(permissionId)
      else currentIds.delete(permissionId)
      return { ...current, permission_ids: Array.from(currentIds).sort((a, b) => a - b) }
    })
  }

  const save = async () => {
    const roleCode = isNew ? generatedRoleCode : role.code?.trim()
    if (!role.name?.trim() || !roleCode) {
      toast.error("Укажите название роли")
      return
    }
    setSaving(true)
    try {
      const payload = {
        code: roleCode,
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
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link href="/roles">Роли и права</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isNew ? "Новая роль" : getRoleName(role)}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div>
            <h1 className="text-2xl font-semibold">{isNew ? "Новая роль" : getRoleName(role)}</h1>
            <p className="mt-1 text-sm text-muted-foreground">Настройка прав доступа для класса пользователей.</p>
          </div>

          <div className="grid max-w-3xl gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Название</Label>
                <Input
                  id="name"
                  value={role.name ?? ""}
                  onChange={(event) => setRole((current) => ({ ...current, name: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Код</Label>
                <Input
                  id="code"
                  value={generatedRoleCode}
                  disabled
                  placeholder="Сгенерируется из названия"
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

          <div className="max-w-5xl space-y-6">
            {groupedPermissions.map(([scope, items]) => (
              <section key={scope} className="space-y-3">
                <h2 className="text-base font-semibold">{scope}</h2>
                <div className="divide-y rounded-md border">
                  {items.map((permission) => (
                    <label key={permission.id} className="flex cursor-pointer items-start gap-3 px-4 py-3 hover:bg-muted/30">
                      <Checkbox
                        className="mt-0.5"
                        checked={selectedIds.has(permission.id)}
                        onCheckedChange={(checked) => togglePermission(permission.id, checked === true)}
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{permission.name}</span>
                        <span className="block text-sm text-muted-foreground">
                          {permission.description || permission.code}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </section>
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
