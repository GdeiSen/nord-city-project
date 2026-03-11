"use client"

import * as React from "react"
import {
  IconDeviceFloppy,
  IconRefresh,
  IconSearch,
} from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { Spinner } from "@/components/ui/spinner"
import { useCanEdit } from "@/hooks"
import { localizationApi, type LocalizationData } from "@/lib/api"

type LocaleValues = Record<string, string>

const TEMPLATE_TOKEN_HTML =
  '<span class="rounded-[2px] bg-amber-300/40 text-amber-800 dark:bg-amber-400/20 dark:text-amber-300">{?}</span>'
const HTML_TAG_PATTERN = /<\/?([a-z][a-z0-9-]*)\b[^>]*>/gi

type TagStyles = {
  bold: number
  italic: number
  underline: number
  strike: number
  code: number
}

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

function getInitialTagStyles(): TagStyles {
  return {
    bold: 0,
    italic: 0,
    underline: 0,
    strike: 0,
    code: 0,
  }
}

function updateTagStyles(styles: TagStyles, tagName: string, isClosing: boolean): void {
  const delta = isClosing ? -1 : 1
  const apply = (key: keyof TagStyles) => {
    styles[key] = Math.max(0, styles[key] + delta)
  }

  switch (tagName) {
    case "b":
    case "strong":
      apply("bold")
      break
    case "i":
    case "em":
      apply("italic")
      break
    case "u":
      apply("underline")
      break
    case "s":
    case "strike":
    case "del":
      apply("strike")
      break
    case "code":
    case "pre":
      apply("code")
      break
    default:
      break
  }
}

function styleClassesToString(styles: TagStyles): string {
  const classes: string[] = []
  if (styles.bold > 0) classes.push("font-semibold")
  if (styles.italic > 0) classes.push("italic")
  if (styles.underline > 0) classes.push("underline")
  if (styles.strike > 0) classes.push("line-through")
  if (styles.code > 0) classes.push("font-mono")
  return classes.join(" ")
}

function renderStyledChunk(chunk: string, styles: TagStyles): string {
  if (!chunk) return ""
  const chunkHtml = escapeHtml(chunk).replace(/\{\?\}/g, TEMPLATE_TOKEN_HTML)
  const classes = styleClassesToString(styles)
  if (!classes) return chunkHtml
  return `<span class="${classes}">${chunkHtml}</span>`
}

function highlightTemplateTokens(value: string): string {
  const source = String(value || "")
  const styles = getInitialTagStyles()
  let html = ""
  let cursor = 0

  HTML_TAG_PATTERN.lastIndex = 0
  let match = HTML_TAG_PATTERN.exec(source)
  while (match) {
    const token = match[0]
    const tagName = String(match[1] || "").toLowerCase()
    const start = match.index ?? 0

    if (start > cursor) {
      html += renderStyledChunk(source.slice(cursor, start), styles)
    }

    const isClosing = token.startsWith("</")
    if (!isClosing) updateTagStyles(styles, tagName, false)
    html += renderStyledChunk(token, styles)
    if (isClosing) updateTagStyles(styles, tagName, true)

    cursor = start + token.length
    match = HTML_TAG_PATTERN.exec(source)
  }

  if (cursor < source.length) {
    html += renderStyledChunk(source.slice(cursor), styles)
  }

  return html || "&nbsp;"
}

function renderDisplayHtml(value: string): string {
  return highlightTemplateTokens(value).replace(/\n/g, "<br/>")
}

function CodeValueInput({
  rowKey,
  value,
  onChange,
  editing,
  onStartEdit,
  onStopEdit,
  disabled = false,
}: {
  rowKey: string
  value: string
  onChange: (nextValue: string) => void
  editing: boolean
  onStartEdit: (key: string) => void
  onStopEdit: () => void
  disabled?: boolean
}) {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)

  const adjustHeight = React.useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = "0px"
    textarea.style.height = `${Math.max(textarea.scrollHeight, 38)}px`
  }, [])

  React.useEffect(() => {
    if (!editing) return
    adjustHeight()
  }, [value, editing, adjustHeight])

  React.useEffect(() => {
    if (!editing) return
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.focus()
    const len = textarea.value.length
    textarea.setSelectionRange(len, len)
  }, [editing])

  if (!editing) {
    return (
      <button
        type="button"
        onClick={() => onStartEdit(rowKey)}
        disabled={disabled}
        className="block w-full rounded-sm px-2 py-1.5 text-left font-mono text-[13px] leading-6 text-foreground hover:bg-muted/40 disabled:cursor-not-allowed"
      >
        <span
          className="block whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: renderDisplayHtml(String(value || "")) }}
        />
      </button>
    )
  }

  return (
    <div className="px-2 py-1.5">
      <textarea
        ref={textareaRef}
        value={value}
        disabled={disabled}
        spellCheck={false}
        onChange={(event) => {
          onChange(event.target.value)
          requestAnimationFrame(adjustHeight)
        }}
        onBlur={onStopEdit}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault()
            onStopEdit()
          }
        }}
        className="block w-full resize-none overflow-hidden rounded-sm border border-border bg-background px-2 py-1.5 font-mono text-[13px] leading-6 text-foreground outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed"
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
  const [search, setSearch] = React.useState("")
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null)
  const [editingKey, setEditingKey] = React.useState<string | null>(null)

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

  const hasChanges = React.useMemo(() => {
    for (const locale of Object.keys(draftData)) {
      const current = draftData[locale] || {}
      const initial = sourceData[locale] || {}
      for (const key of Object.keys(current)) {
        if (current[key] !== initial[key]) return true
      }
    }
    return false
  }, [draftData, sourceData])

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
    setEditingKey(null)
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
      setEditingKey(null)
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
                  Компактный режим редактирования. Плейсхолдеры <code>{"{?}"}</code> подсвечены.
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
                <div className="overflow-hidden rounded-md border bg-card">
                  <div className="flex items-center justify-between border-b px-3 py-2 text-xs font-mono text-muted-foreground">
                    <span>{activeLocale || "Локаль не выбрана"}</span>
                    <span>{filteredKeys.length} ключей</span>
                  </div>
                  <div className="max-h-[70vh] overflow-auto">
                    {loading ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyMedia variant="icon">
                              <Spinner className="size-5" />
                            </EmptyMedia>
                            <EmptyTitle>Загрузка локализации</EmptyTitle>
                            <EmptyDescription>
                              Пожалуйста, подождите. Получаем данные бота.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : localeNames.length === 0 ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyTitle>Локализация пуста</EmptyTitle>
                            <EmptyDescription>
                              Проверьте данные на стороне `bot_service`.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : filteredKeys.length === 0 ? (
                      <div className="px-2 py-6">
                        <Empty className="w-full border-0 py-6">
                          <EmptyHeader>
                            <EmptyMedia variant="icon">
                              <IconSearch className="size-5" />
                            </EmptyMedia>
                            <EmptyTitle>Ничего не найдено</EmptyTitle>
                            <EmptyDescription>
                              Измените поисковый запрос, чтобы увидеть ключи локализации.
                            </EmptyDescription>
                          </EmptyHeader>
                        </Empty>
                      </div>
                    ) : (
                      <div className="divide-y">
                        {filteredKeys.map((key, index) => {
                          const value = currentValues[key] ?? ""
                          const isChanged = value !== (sourceValues[key] ?? "")
                          return (
                            <div
                              key={key}
                              className={`grid grid-cols-[32px_minmax(220px,320px)_1fr] items-start gap-1.5 pl-0.5 pr-2 py-1 ${
                                isChanged ? "bg-yellow-200/45 dark:bg-yellow-500/15" : ""
                              }`}
                            >
                              <div className="pt-2 pr-1 text-right font-mono text-[11px] text-muted-foreground">
                                {index + 1}
                              </div>
                              <div className="pt-2 pr-1 font-mono text-[12px] break-all text-foreground/80">
                                "{key}"
                              </div>
                              <CodeValueInput
                                rowKey={key}
                                value={value}
                                disabled={saving || loading}
                                editing={editingKey === key}
                                onStartEdit={(targetKey) => setEditingKey(targetKey)}
                                onStopEdit={() => setEditingKey((current) => (current === key ? null : current))}
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
