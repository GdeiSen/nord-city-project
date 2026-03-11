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
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit } from "@/hooks"
import { localizationApi, type LocalizationData } from "@/lib/api"

type LocaleValues = Record<string, string>

const TEMPLATE_TOKEN_HTML =
  '<span class="rounded bg-amber-400/15 px-1 text-amber-300">{?}</span>'

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

function highlightTemplateTokens(value: string): string {
  return escapeHtml(value).replace(/\{\?\}/g, TEMPLATE_TOKEN_HTML)
}

function buildPreviewHtml(value: string): string {
  const rawValue = String(value ?? "")
  const hasHtml = /<\/?[a-z][\s\S]*>/i.test(rawValue)
  if (!hasHtml) {
    return highlightTemplateTokens(rawValue).replace(/\n/g, "<br/>")
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
  return doc.body.innerHTML.replace(/\{\?\}/g, TEMPLATE_TOKEN_HTML)
}

function CodeValueInput({
  value,
  onChange,
  disabled = false,
}: {
  value: string
  onChange: (nextValue: string) => void
  disabled?: boolean
}) {
  const preRef = React.useRef<HTMLPreElement | null>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)

  const syncScroll = React.useCallback(() => {
    const pre = preRef.current
    const textarea = textareaRef.current
    if (!pre || !textarea) return
    pre.scrollTop = textarea.scrollTop
    pre.scrollLeft = textarea.scrollLeft
  }, [])

  const adjustHeight = React.useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = "0px"
    textarea.style.height = `${Math.max(textarea.scrollHeight, 38)}px`
    syncScroll()
  }, [syncScroll])

  React.useEffect(() => {
    adjustHeight()
  }, [value, adjustHeight])

  const highlightedValue = React.useMemo(() => {
    const prepared = highlightTemplateTokens(String(value || ""))
    return prepared || "&nbsp;"
  }, [value])

  return (
    <div className="relative">
      <pre
        ref={preRef}
        className="m-0 min-h-[38px] overflow-hidden whitespace-pre-wrap break-words px-2 py-1.5 font-mono text-[13px] leading-6 text-slate-200"
        dangerouslySetInnerHTML={{ __html: highlightedValue }}
      />
      <textarea
        ref={textareaRef}
        value={value}
        disabled={disabled}
        spellCheck={false}
        onChange={(event) => {
          onChange(event.target.value)
          requestAnimationFrame(adjustHeight)
        }}
        onScroll={syncScroll}
        className="absolute inset-0 w-full resize-none overflow-hidden border-0 bg-transparent px-2 py-1.5 font-mono text-[13px] leading-6 text-transparent caret-slate-100 outline-none focus:bg-slate-900/20 disabled:cursor-not-allowed"
      />
    </div>
  )
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
                  Компактный режим редактирования в стиле code editor. Плейсхолдеры <code>{"{?}"}</code>{" "}
                  подсвечены.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-[220px] max-w-md flex-1">
                  <IconSearch className="pointer-events-none absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Поиск по ключу или значению"
                    className="h-9 pl-8"
                  />
                </div>

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 px-3"
                  onClick={() => setPreviewMode((current) => !current)}
                  disabled={loading || !!errorMessage}
                >
                  {previewMode ? <IconCode className="h-4 w-4" /> : <IconEye className="h-4 w-4" />}
                  {previewMode ? "JSON" : "Просмотр"}
                </Button>

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 px-3"
                  onClick={loadLocalization}
                  disabled={loading || saving}
                >
                  <IconRefresh className="h-4 w-4" />
                  Обновить
                </Button>

                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 px-3"
                  onClick={handleReset}
                  disabled={!hasChanges || loading || saving}
                >
                  Сбросить
                </Button>

                <Button
                  type="button"
                  size="sm"
                  className="h-9 px-3"
                  onClick={handleSave}
                  disabled={!hasChanges || loading || saving}
                >
                  <IconDeviceFloppy className="h-4 w-4" />
                  {saving ? "Сохранение..." : "Сохранить"}
                </Button>

                <Badge variant={hasChanges ? "default" : "secondary"} className="h-9 px-3 text-sm">
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
                      className="h-8 px-3"
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
                <div className="overflow-hidden rounded-md border border-slate-700 bg-slate-950/95">
                  <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-xs font-mono text-slate-400">
                    <span>{activeLocale || "Локаль не выбрана"}</span>
                    <span>{filteredKeys.length} ключей</span>
                  </div>
                  <div className="max-h-[70vh] overflow-auto">
                    {loading ? (
                      <p className="px-3 py-4 text-sm text-slate-400">Загрузка...</p>
                    ) : localeNames.length === 0 ? (
                      <p className="px-3 py-4 text-sm text-slate-400">
                        Локализация пуста. Проверьте данные в `bot_service`.
                      </p>
                    ) : filteredKeys.length === 0 ? (
                      <p className="px-3 py-4 text-sm text-slate-400">Нет совпадений по фильтру.</p>
                    ) : previewMode ? (
                      <div className="divide-y divide-slate-800/70">
                        {filteredKeys.map((key, index) => (
                          <div
                            key={key}
                            className="grid grid-cols-[48px_minmax(220px,320px)_1fr] items-start gap-2 px-2 py-1.5"
                          >
                            <div className="pt-1.5 text-right font-mono text-[11px] text-slate-500">
                              {index + 1}
                            </div>
                            <div className="pt-1.5 pr-2 font-mono text-[12px] break-all text-sky-300">
                              "{key}"
                            </div>
                            <div
                              className="px-2 py-1.5 text-sm leading-6 break-words text-slate-200 [&_a]:underline [&_b]:font-semibold [&_i]:italic [&_code]:rounded [&_code]:bg-slate-800 [&_code]:px-1 [&_ul]:list-disc [&_ul]:pl-5"
                              dangerouslySetInnerHTML={{ __html: previewHtmlByKey[key] || "" }}
                            />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="divide-y divide-slate-800/70">
                        {filteredKeys.map((key, index) => {
                          const value = currentValues[key] ?? ""
                          const isChanged = value !== (sourceValues[key] ?? "")
                          return (
                            <div
                              key={key}
                              className={`grid grid-cols-[48px_minmax(220px,320px)_1fr] items-start gap-2 px-2 py-1 ${
                                isChanged ? "bg-emerald-500/5" : ""
                              }`}
                            >
                              <div className="pt-2 text-right font-mono text-[11px] text-slate-500">
                                {index + 1}
                              </div>
                              <div className="pt-2 pr-2 font-mono text-[12px] break-all text-sky-300">
                                "{key}"
                              </div>
                              <CodeValueInput
                                value={value}
                                disabled={saving || loading}
                                onChange={(nextValue) => handleValueChange(key, nextValue)}
                              />
                            </div>
                          )
                        })}
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
