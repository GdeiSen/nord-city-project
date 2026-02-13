"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconEdit } from "@tabler/icons-react"
import { User, USER_ROLES, ROLE_LABELS, ROLE_BADGE_VARIANTS } from "@/types"
import { userApi, rentalObjectApi } from "@/lib/api"
import { useLoading } from "@/hooks/use-loading"
import { useCanEdit } from "@/hooks/use-can-edit"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"

function getRoleBadge(role: number | undefined) {
  const badgeClass = "text-sm px-3 py-1"
  if (role === undefined) return <Badge variant="outline" className={badgeClass}>Неопределен</Badge>
  const roleKey = Object.values(USER_ROLES).find((r) => r === role)
  if (!roleKey) return <Badge variant="outline" className={badgeClass}>Неизвестная роль</Badge>
  return <Badge variant={ROLE_BADGE_VARIANTS[roleKey]} className={badgeClass}>{ROLE_LABELS[roleKey]}</Badge>
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function UserDetailPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const userId = Number(params?.id)
  const { loading, withLoading } = useLoading(true)
  const canEdit = useCanEdit()
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    if (!userId || Number.isNaN(userId)) return
    withLoading(async () => {
      const [userData, objects] = await Promise.all([
        userApi.getById(userId),
        rentalObjectApi.getAll(),
      ])
      const obj = objects.find((o) => o.id === userData.object_id)
      setUser({
        ...userData,
        object: obj,
      } as User)
    }).catch((err: any) => {
      toast.error("Не удалось загрузить пользователя", { description: err?.message })
      router.push("/users")
    })
  }, [userId])

  if (Number.isNaN(userId)) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
            <p className="text-lg font-medium">Пользователь не найден</p>
            <p className="text-sm text-muted-foreground">Некорректный идентификатор.</p>
            <Link href="/users" className="text-sm text-primary hover:underline">
              К списку пользователей
            </Link>
          </div>
        </SidebarInset>
        <Toaster />
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem>
                  <BreadcrumbLink asChild>
                    <Link href="/users">Пользователи</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                <BreadcrumbItem>
                  <BreadcrumbPage>#{userId}</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb>
            {canEdit && (
              <Button asChild size="sm">
                <Link href={`/users/edit/${userId}`} className="gap-2">
                  <IconEdit className="h-4 w-4" />
                  Редактировать
                </Link>
              </Button>
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : user ? (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">
                  {user.last_name} {user.first_name} {user.middle_name}
                </h1>
                <p className="text-sm text-muted-foreground mt-1">
                  @{user.username} · Создан {formatDate(user.created_at)}
                  {user.updated_at !== user.created_at && (
                    <> · Обновлён {formatDate(user.updated_at)}</>
                  )}
                </p>
                <div className="mt-3">{getRoleBadge(user.role)}</div>
              </div>
              <div className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Email</div>
                    <p className="text-sm">{user.email || "—"}</p>
                  </div>
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Телефон</div>
                    <p className="text-sm">{user.phone_number || "—"}</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Объект</div>
                  <p className="text-sm">{user.object_id ? `БЦ-${user.object_id}` : "Не назначен"}</p>
                </div>
                {user.legal_entity && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground">Юр. лицо</div>
                    <p className="text-sm">{user.legal_entity}</p>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
