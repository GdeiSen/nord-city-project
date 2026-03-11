"use client"

import * as React from "react"
import {
  IconCode,
  IconDeviceFloppy,
  IconEye,
  IconRefresh,
  IconSearch,
} from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SidebarInset } from "@/components/ui/sidebar"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit } from "@/hooks"
import { localizationApi, type LocalizationData } from "@/lib/api"

type LocaleValues = Record<string, string>

function cloneLocalization(data: LocalizationData): LocalizationData {
  const next: LocalizationData = {}
  for (const [locale, values] of Object.entries(data || {})) {
    next[locale] = { ...(values || {}) }
  }
  return next
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;")
}

function buildPreviewHtml(value: string): string {
  const rawValue = String(value ?? "")
  const hasHtml = /<\/?[a-z][\s\S]*>/i.test(rawValue)
  if (!hasHtml) {
    return escapeHtml(rawValue).replace(/\n/g, "<br/>")
  }

  if (typeof window === "undefined") {
    return rawValue
  }

  const parser = new window.DOMParser()
  const doc = parser.parseFromString(rawValue, "text/html")
  doc.querySelectorAll("script, style, iframe, object, embed").forEach((node) => node.remove())
  doc.querySelectorAll("*").forEach((element) => {
    for (const attr of Array.from(element.attributes)) {
      const attrName = attr.name.toLowerCase()
      if (attrName.startsWith("on")) {
        element.removeAttribute(attr.name)
        continue
      }
      if ((attrName === "href" || attrName === "src") && /^\s*javascript:/i.test(attr.value)) {
        element.removeAttribute(attr.name)
      }
    }
  })
  return doc.body.innerHTML
}

export default function LocalizationPage() {
  const canEditLocalization = useCanEdit()

  const [sourceData, setSourceData] = React.useState<LocalizationData>({})
  const [draftData, setDraftData] = React.useState<LocalizationData>({})
  const [activeLocale, setActiveLocale] = React.useState("")
  const [loading, setLoading] = React.useState(true)
  const [saving, setSaving] = React.useState(false)
  const [previewMode, setPreviewMode] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)

  const loadLocalization = React.useCallback(async () => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const data = await localizationApi.get()
      const normalized = cloneLocalization(data || {})
      const locales = Object.keys(normalized)
      setSourceData(normalized)
      setDraftData(cloneLocalization(normalized))
      setActiveLocale((currentLocale) =>
        currentLocale && locales.includes(currentLocale) ? currentLocale : (locales[0] ?? "")
      )
    } catch (error: any) {
      const message = error?.message ?? "Не удалось загрузить локализацию."
      setErrorMessage(message)
      toast.error("Ошибка загрузки локализации", { description: message })
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    if (!canEditLocalization) {
      setLoading(false)
      return
    }
    loadLocalization()
  }, [canEditLocalization, loadLocalization])

  const localeNames = React.useMemo(() => Object.keys(draftData), [draftData])

  React.useEffect(() => {
    if (!localeNames.length) {
      if (activeLocale) setActiveLocale("")
      return
    }
    if (!activeLocale || !localeNames.includes(activeLocale)) {
      setActiveLocale(localeNames[0])
    }
  }, [activeLocale, localeNames])

  const currentValues: LocaleValues = React.useMemo(
    () => draftData[activeLocale] || {},
    [draftData, activeLocale]
  )

  const sourceValues: LocaleValues = React.useMemo(
    () => sourceData[activeLocale] || {},
    [sourceData, activeLocale]
  )

  const filteredKeys = React.useMemo(() => {
    const query = search.trim().toLowerCase()
    const keys = Object.keys(currentValues)
    if (!query) return keys
    return keys.filter((key) => {
      const value = currentValues[key] ?? ""
      return key.toLowerCase().includes(query) || value.toLowerCase().includes(query)
    })
  }, [currentValues, search])

  const changedKeysCount = React.useMemo(() => {
    let count = 0
    for (const locale of Object.keys(draftData)) {
      const current = draftData[locale] || {}
      const initial = sourceData[locale] || {}
      for (const key of Object.keys(current)) {
        if (current[key] !== initial[key]) count += 1
      }
    }
    return count
  }, [draftData, sourceData])

  const hasChanges = changedKeysCount > 0

  const previewHtmlByKey = React.useMemo(() => {
    if (!previewMode) return {}
    const next: Record<string, string> = {}
    for (const key of filteredKeys) {
      next[key] = buildPreviewHtml(currentValues[key] ?? "")
    }
    return next
  }, [previewMode, filteredKeys, currentValues])

  const handleValueChange = (key: string, value: string) => {
    setDraftData((prev) => ({
      ...prev,
      [activeLocale]: {
        ...(prev[activeLocale] || {}),
        [key]: value,
      },
    }))
  }

  const handleReset = () => {
    setDraftData(cloneLocalization(sourceData))
    toast.success("Изменения отменены")
  }

  const handleSave = async () => {
    if (!hasChanges || saving) return
    setSaving(true)
    try {
      const updated = await localizationApi.update(draftData)
      const normalized = cloneLocalization(updated || {})
      setSourceData(normalized)
      setDraftData(cloneLocalization(normalized))
      toast.success("Локализация сохранена")
    } catch (error: any) {
      toast.error("Не удалось сохранить локализацию", {
        description: error?.message ?? "Попробуйте еще раз.",
      })
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
          {!canEditLocalization ? (
            <Alert variant="destructive">
              <AlertTitle>Доступ ограничен</AlertTitle>
              <AlertDescription>
                Редактор локализации доступен только администраторам и super admin.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="w-full min-w-0 space-y-4">
              <div className="space-y-1">
                <h1 className="text-2xl font-semibold">Редактор локализации</h1>
                <p className="text-sm text-muted-foreground">
                  Редактируйте значения сообщений бота. Имена ключей зафиксированы и не изменяются.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative w-full min-w-[240px] max-w-md">
                  <IconSearch className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Поиск по ключу или значению"
                    className="pl-8"
                  />
                </div>

                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setPreviewMode((current) => !current)}
                  disabled={loading || !!errorMessage}
                >
                  {previewMode ? <IconCode className="h-4 w-4" /> : <IconEye className="h-4 w-4" />}
                  {previewMode ? "Режим JSON" : "Режим предпросмотра"}
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  onClick={loadLocalization}
                  disabled={loading || saving}
                >
                  <IconRefresh className="h-4 w-4" />
                  Обновить
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={!hasChanges || loading || saving}
                >
                  Сбросить
                </Button>

                <Button type="button" onClick={handleSave} disabled={!hasChanges || loading || saving}>
                  <IconDeviceFloppy className="h-4 w-4" />
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>

                <Badge variant={hasChanges ? "default" : "secondary"}>
                  Изменено: {changedKeysCount}
                </Badge>
              </div>

              {localeNames.length > 1 && (
                <div className="flex flex-wrap items-center gap-2">
                  {localeNames.map((locale) => (
                    <Button
                      key={locale}
                      type="button"
                      size="sm"
                      variant={activeLocale === locale ? "default" : "outline"}
                      onClick={() => setActiveLocale(locale)}
                    >
                      {locale}
                    </Button>
                  ))}
                </div>
              )}

              {errorMessage ? (
                <Alert variant="destructive">
                  <AlertTitle>Ошибка</AlertTitle>
                  <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
              ) : (
                <div className="rounded-lg border">
                  <div className="border-b px-4 py-2 text-sm text-muted-foreground">
                    {activeLocale || "Локаль не выбрана"}
                  </div>
                  <div className="max-h-[68vh] overflow-auto p-4">
                    {loading ? (
                      <p className="text-sm text-muted-foreground">Загрузка...</p>
                    ) : localeNames.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        Локализация пуста. Проверьте данные в `bot_service`.
                      </p>
                    ) : previewMode ? (
                      <div className="space-y-3">
                        {filteredKeys.length === 0 ? (
                          <p className="text-sm text-muted-foreground">Нет совпадений по фильтру.</p>
                        ) : (
                          filteredKeys.map((key) => (
                            <div key={key} className="rounded-md border p-3">
                              <div className="mb-2 font-mono text-xs text-muted-foreground">"{key}"</div>
                              <div
                                className="rounded-md border bg-background px-3 py-2 text-sm leading-6 break-words [&_a]:underline [&_b]:font-semibold [&_i]:italic [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_ul]:list-disc [&_ul]:pl-5"
                                dangerouslySetInnerHTML={{ __html: previewHtmlByKey[key] || "" }}
                              />
                            </div>
                          ))
                        )}
                      </div>
                    ) : (
                      <div className="space-y-2 font-mono text-[13px]">
                        <div className="text-muted-foreground">{"{"}</div>
                        <div className="pl-4">
                          <span className="text-amber-600 dark:text-amber-400">"{activeLocale}"</span>
                          <span className="text-muted-foreground">: {"{"}</span>
                        </div>
                        <div className="space-y-3 pl-8">
                          {filteredKeys.length === 0 ? (
                            <p className="text-sm text-muted-foreground">Нет совпадений по фильтру.</p>
                          ) : (
                            filteredKeys.map((key) => {
                              const value = currentValues[key] ?? ""
                              const isChanged = value !== (sourceValues[key] ?? "")
                              return (
                                <div
                                  key={key}
                                  className={`rounded-md border p-3 ${
                                    isChanged ? "border-primary/60 bg-primary/5" : ""
                                  }`}
                                >
                                  <div className="mb-2 flex items-start gap-2">
                                    <span className="select-text break-all text-sky-700 dark:text-sky-300">
                                      "{key}"
                                    </span>
                                    <span className="text-muted-foreground">:</span>
                                  </div>
                                  <Textarea
                                    value={value}
                                    onChange={(event) => handleValueChange(key, event.target.value)}
                                    className="min-h-[96px] resize-y font-mono text-[13px] leading-5"
                                  />
                                </div>
                              )
                            })
                          )}
                        </div>
                        <div className="pl-4 text-muted-foreground">{"}"}</div>
                        <div className="text-muted-foreground">{"}"}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
