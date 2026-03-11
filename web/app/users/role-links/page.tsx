"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { useIsSuperAdmin } from "@/hooks"
import { UserRoleLinksResponse, userApi } from "@/lib/api"
import { IconCheck, IconCopy, IconLink } from "@tabler/icons-react"
import { toast } from "sonner"

export default function UserRoleLinksPage() {
  const isSuperAdmin = useIsSuperAdmin()
  const [loading, setLoading] = useState(true)
  const [roleLinks, setRoleLinks] = useState<UserRoleLinksResponse | null>(null)
  const [copiedRoleCode, setCopiedRoleCode] = useState<string | null>(null)

  useEffect(() => {
    if (!isSuperAdmin) {
      setLoading(false)
      return
    }

    let active = true
    userApi
      .getRoleLinks()
      .then((data) => {
        if (!active) return
        setRoleLinks(data)
      })
      .catch((error: any) => {
        toast.error("Не удалось загрузить ссылки ролей", { description: error?.message })
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [isSuperAdmin])

  const handleCopy = async (roleCode: string, url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopiedRoleCode(roleCode)
      toast.success("Ссылка скопирована")
      window.setTimeout(() => setCopiedRoleCode((prev) => (prev === roleCode ? null : prev)), 1200)
    } catch {
      toast.error("Не удалось скопировать ссылку")
    }
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link href="/users">Пользователи</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Ссылки ролей</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="space-y-1">
            <h2 className="text-3xl font-bold tracking-tight">Ссылки ролей пользователей</h2>
            <p className="text-muted-foreground">
              Ссылки для автоприсвоения роли при первом запуске бота через deep-link.
            </p>
          </div>

          {!isSuperAdmin ? (
            <div className="text-sm text-destructive">Доступ только для Super Admin.</div>
          ) : loading ? (
            <Empty className="w-full border py-8">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconLink className="h-5 w-5" />
                </EmptyMedia>
                <EmptyTitle>Загрузка ссылок</EmptyTitle>
                <EmptyDescription>Получаем параметры deep-link из конфигурации.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : !roleLinks?.links?.length ? (
            <Empty className="w-full border py-8">
              <EmptyHeader>
                <EmptyTitle>Ссылки не настроены</EmptyTitle>
                <EmptyDescription>Проверьте BOT_USERNAME и токены deep-link в .env.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {roleLinks.links.map((item) => (
                <Card key={item.role_code}>
                  <CardHeader className="space-y-2">
                    <CardTitle>{item.title}</CardTitle>
                    <CardDescription>{item.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-md border bg-muted/20 px-3 py-2 font-mono text-sm break-all">
                      {item.url}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button type="button" onClick={() => handleCopy(item.role_code, item.url)}>
                        {copiedRoleCode === item.role_code ? (
                          <IconCheck className="h-4 w-4" />
                        ) : (
                          <IconCopy className="h-4 w-4" />
                        )}
                        {copiedRoleCode === item.role_code ? "Скопировано" : "Скопировать"}
                      </Button>
                      <Button type="button" variant="outline" asChild>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          Открыть ссылку
                        </a>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
