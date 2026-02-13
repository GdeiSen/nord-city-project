"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconChevronLeft, IconEdit, IconUser } from "@tabler/icons-react"
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
  if (role === undefined) return <Badge variant="outline">Неопределен</Badge>
  const roleKey = Object.values(USER_ROLES).find((r) => r === role)
  if (!roleKey) return <Badge variant="outline">Неизвестная роль</Badge>
  return <Badge variant={ROLE_BADGE_VARIANTS[roleKey]}>{ROLE_LABELS[roleKey]}</Badge>
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
      <div className="flex min-h-screen items-center justify-center">
        <Card>
          <CardHeader>
            <CardTitle>Пользователь не найден</CardTitle>
            <CardDescription>Некорректный идентификатор.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => router.push("/users")}>
              К списку пользователей
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
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

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/users" className="gap-2">
                <IconChevronLeft className="h-4 w-4" />
                Назад к списку
              </Link>
            </Button>
            {canEdit && (
              <Button asChild>
                <Link href={`/users/edit/${userId}`} className="gap-2">
                  <IconEdit className="h-4 w-4" />
                  Редактировать
                </Link>
              </Button>
            )}
          </div>

          {loading ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </CardContent>
            </Card>
          ) : user ? (
            <Card>
              <CardHeader>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <CardTitle className="flex items-center gap-2">
                    <IconUser className="h-6 w-6" />
                    {user.last_name} {user.first_name} {user.middle_name}
                  </CardTitle>
                  {getRoleBadge(user.role)}
                </div>
                <CardDescription>
                  @{user.username} · Создан {formatDate(user.created_at)}
                  {user.updated_at !== user.created_at && (
                    <> · Обновлён {formatDate(user.updated_at)}</>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
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
              </CardContent>
            </Card>
          ) : null}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
