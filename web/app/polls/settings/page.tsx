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
import { Textarea } from "@/components/ui/textarea"
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
const GOOGLE_FORMS_URL_REGEX_GLOBAL = /https?:\/\/(?:forms\.gle\/[^\s]+|docs\.google\.com\/forms\/[^\s]+)/gi
const ANY_URL_REGEX_GLOBAL = /https?:\/\/[^\s]+/gi

function isValidGoogleFormsUrl(url: string): boolean {
  return GOOGLE_FORMS_URL_REGEX.test((url || "").trim())
}

function extractGoogleFormsUrls(text: string): string[] {
  return String(text || "").match(GOOGLE_FORMS_URL_REGEX_GLOBAL) ?? []
}

function extractAllUrls(text: string): string[] {
  return String(text || "").match(ANY_URL_REGEX_GLOBAL) ?? []
}

export default function PollSettingsPage() {
  const router = useRouter()
  const canEdit = useCanEdit()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [googleFormUrl, setGoogleFormUrl] = useState("")
  const [pollHeader, setPollHeader] = useState("")
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
        setPollHeader(data.poll_header || "")
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

  const editorLineCount = useMemo(
    () => Math.max(1, pollHeader.split("\n").length),
    [pollHeader]
  )

  const validationError = useMemo(() => {
    const trimmedHeader = pollHeader.trim()
    if (!trimmedHeader) {
      return "Введите сообщение, которое бот отправляет вместе со ссылкой на опрос."
    }

    const allUrls = extractAllUrls(trimmedHeader)
    const googleUrls = extractGoogleFormsUrls(trimmedHeader)

    if (allUrls.length !== 1 || googleUrls.length !== 1) {
      return "Сообщение должно содержать ровно одну ссылку, и она должна вести на Google Форму."
    }

    const detectedUrl = googleUrls[0]?.trim() || ""
    if (!isValidGoogleFormsUrl(detectedUrl)) {
      return "Допустимы только ссылки вида forms.gle/... или docs.google.com/forms/..."
    }

    return ""
  }, [pollHeader])

  const handleSave = async () => {
    if (validationError) {
      toast.error(validationError)
      return
    }

    const detectedUrl = extractGoogleFormsUrls(pollHeader)[0]?.trim() || ""

    setSaving(true)
    try {
      const response = await pollApi.updateGoogleFormSettings(
        detectedUrl,
        pollHeader.trim()
      )
      setGoogleFormUrl(response.google_form_url || "")
      setPollHeader(response.poll_header || "")
      setLocale(response.locale || "RU")
      toast.success("Сообщение опроса обновлено")
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
                  Сообщение сохраняется в локализации бота (ключ <span className="font-mono">{locale}.poll_header</span>).
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="google_form_url">Обнаруженная ссылка на Google Форму</Label>
                <Input
                  id="google_form_url"
                  type="text"
                  value={googleFormUrl}
                  readOnly
                  disabled
                />
                <p className="text-sm text-muted-foreground">
                  Поле обновляется автоматически на основе текста сообщения ниже.
                </p>
              </div>

              <div className="space-y-2">
                <Label>Сообщение с ссылкой на Google Форму</Label>
                <div className="grid min-h-[340px] grid-cols-[44px_minmax(0,1fr)] overflow-hidden rounded-md border border-border bg-muted/20">
                  <div className="select-none border-r border-border/80 bg-muted/10 px-2 py-2 text-right font-mono text-[12px] leading-6 text-muted-foreground">
                    {Array.from({ length: editorLineCount }, (_, index) => (
                      <div key={index + 1}>{index + 1}</div>
                    ))}
                  </div>
                  <div className="overflow-x-auto">
                    <Textarea
                      value={pollHeader}
                      spellCheck={false}
                      wrap="off"
                      onChange={(e) => {
                        const nextValue = e.target.value
                        setPollHeader(nextValue)
                        const nextUrl = extractGoogleFormsUrls(nextValue)[0]?.trim() || ""
                        setGoogleFormUrl(nextUrl)
                      }}
                      className="min-h-[340px] min-w-full resize-y rounded-none border-0 bg-transparent font-mono whitespace-pre text-[13px] leading-6 shadow-none focus-visible:ring-0"
                    />
                  </div>
                </div>
                {validationError ? (
                  <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                    {validationError}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Допускается свободное редактирование текста сообщения, но в нем должна
                    оставаться ровно одна корректная ссылка на Google Форму.
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
