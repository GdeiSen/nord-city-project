"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { IconLink } from "@tabler/icons-react"
import { toast } from "sonner"

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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit } from "@/hooks"
import { pollApi } from "@/lib/api"

const GOOGLE_FORMS_URL_REGEX = /^https?:\/\/(?:forms\.gle\/[^\s]+|docs\.google\.com\/forms\/[^\s]+)$/i

function isValidGoogleFormsUrl(url: string): boolean {
  return GOOGLE_FORMS_URL_REGEX.test((url || "").trim())
}

export default function PollSettingsPage() {
  const router = useRouter()
  const canEdit = useCanEdit()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [googleFormUrl, setGoogleFormUrl] = useState("")
  const [locale, setLocale] = useState("RU")

  useEffect(() => {
    if (!canEdit) {
      setLoading(false)
      return
    }

    let active = true
    pollApi
      .getGoogleFormSettings()
      .then((data) => {
        if (!active) return
        setGoogleFormUrl(data.google_form_url || "")
        setLocale(data.locale || "RU")
      })
      .catch((error: any) => {
        toast.error("Не удалось загрузить настройки опроса", { description: error?.message })
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [canEdit])

  const validationError = useMemo(() => {
    const value = googleFormUrl.trim()
    if (!value) return "Укажите ссылку на Google Форму."
    if (!isValidGoogleFormsUrl(value)) {
      return "Допустимы только ссылки вида forms.gle/... или docs.google.com/forms/..."
    }
    return ""
  }, [googleFormUrl])

  const handleSave = async () => {
    if (validationError) {
      toast.error(validationError)
      return
    }

    setSaving(true)
    try {
      const response = await pollApi.updateGoogleFormSettings(googleFormUrl.trim())
      setGoogleFormUrl(response.google_form_url || "")
      setLocale(response.locale || "RU")
      toast.success("Ссылка на опрос обновлена")
      router.push("/polls")
    } catch (error: any) {
      toast.error("Не удалось сохранить настройки", { description: error?.message })
    } finally {
      setSaving(false)
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
                  <Link href="/polls">Опросы</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Настройки</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          {!canEdit ? (
            <div className="text-sm text-destructive">Доступ только для администраторов.</div>
          ) : loading ? (
            <Empty className="w-full border py-8">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconLink className="h-5 w-5" />
                </EmptyMedia>
                <EmptyTitle>Загрузка настроек опроса</EmptyTitle>
                <EmptyDescription>Читаем текущую ссылку из poll_header в локализации бота.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <div className="w-full min-w-0 max-w-2xl space-y-6">
              <div>
                <h1 className="text-2xl font-semibold">Настройки Google-опроса</h1>
                <p className="text-sm text-muted-foreground mt-1">
                  Ссылка сохраняется в локализации бота (ключ <span className="font-mono">{locale}.poll_header</span>).
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="google_form_url">Ссылка на Google Форму</Label>
                <Input
                  id="google_form_url"
                  type="url"
                  placeholder="https://forms.gle/..."
                  value={googleFormUrl}
                  onChange={(e) => setGoogleFormUrl(e.target.value)}
                />
                {validationError ? (
                  <p className="text-sm text-destructive">{validationError}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    При сохранении предыдущие ссылки Google Форм удаляются, остается только новая.
                  </p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button type="button" onClick={handleSave} disabled={saving}>
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
