"use client"

import Link from "next/link"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { SidebarInset } from "@/components/ui/sidebar"
import { Switch } from "@/components/ui/switch"
import { Toaster } from "@/components/ui/sonner"
import { useCanEdit } from "@/hooks"
import { botSettingsApi, type BotSettingsData } from "@/lib/api"

const FEATURE_DEFINITIONS = [
  {
    key: "profile",
    title: "Профиль",
    description:
      "Личные данные пользователя и первичное заполнение профиля. Если выключить этот раздел, новые пользователи не смогут дозаполнить профиль в боте.",
  },
  {
    key: "service",
    title: "Обслуживание",
    description: "Создание заявок на обслуживание и ремонт через бота.",
  },
  {
    key: "poll",
    title: "Опрос",
    description: "Переход в раздел опроса из главного меню бота.",
  },
  {
    key: "feedback",
    title: "Обратная связь",
    description: "Отправка предложений и замечаний через раздел обратной связи.",
  },
  {
    key: "guest_parking",
    title: "Гостевая парковка",
    description: "Оформление заявок на гостевую парковку из главного меню.",
  },
  {
    key: "spaces",
    title: "Свободные площади",
    description: "Просмотр свободных площадей и карточек помещений.",
  },
] as const

function createDefaultSettings(): BotSettingsData {
  return {
    features: Object.fromEntries(
      FEATURE_DEFINITIONS.map((feature) => [feature.key, { enabled: true }])
    ),
  }
}

function normalizeSettings(data?: Partial<BotSettingsData> | null): BotSettingsData {
  const normalized = createDefaultSettings()
  const features = data?.features ?? {}

  for (const feature of FEATURE_DEFINITIONS) {
    const rawValue = features[feature.key]
    if (typeof rawValue?.enabled === "boolean") {
      normalized.features[feature.key] = { enabled: rawValue.enabled }
    }
  }

  return normalized
}

function cloneSettings(data: BotSettingsData): BotSettingsData {
  return {
    features: Object.fromEntries(
      Object.entries(data.features || {}).map(([key, value]) => [
        key,
        { enabled: !!value?.enabled },
      ])
    ),
  }
}

export default function BotSettingsPage() {
  const canEdit = useCanEdit()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [sourceData, setSourceData] = useState<BotSettingsData>(createDefaultSettings())
  const [draftData, setDraftData] = useState<BotSettingsData>(createDefaultSettings())

  const loadSettings = useCallback(async () => {
    setLoading(true)
    try {
      const data = normalizeSettings(await botSettingsApi.get())
      setSourceData(cloneSettings(data))
      setDraftData(cloneSettings(data))
    } catch (error: any) {
      toast.error("Не удалось загрузить настройки бота", {
        description: error?.message ?? "Попробуйте позже.",
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!canEdit) {
      setLoading(false)
      return
    }
    loadSettings()
  }, [canEdit, loadSettings])

  const hasChanges = useMemo(
    () => JSON.stringify(sourceData) !== JSON.stringify(draftData),
    [draftData, sourceData]
  )

  const handleToggle = (featureKey: string, enabled: boolean) => {
    setDraftData((current) => ({
      features: {
        ...current.features,
        [featureKey]: { enabled },
      },
    }))
  }

  const handleReset = () => {
    setDraftData(cloneSettings(sourceData))
    toast.success("Изменения отменены")
  }

  const handleSave = async () => {
    if (!hasChanges || saving) return

    setSaving(true)
    try {
      const updated = normalizeSettings(await botSettingsApi.update(draftData))
      setSourceData(cloneSettings(updated))
      setDraftData(cloneSettings(updated))
      toast.success("Настройки бота сохранены")
    } catch (error: any) {
      toast.error("Не удалось сохранить настройки бота", {
        description: error?.message ?? "Попробуйте позже.",
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
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink asChild>
                  <Link href="/localization">Локализация бота</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Настройки бота</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          {!canEdit ? (
            <Alert variant="destructive">
              <AlertTitle>Доступ ограничен</AlertTitle>
              <AlertDescription>
                Настройки бота доступны только администраторам и super admin.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="w-full min-w-0 max-w-4xl space-y-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="space-y-1">
                  <h1 className="text-2xl font-semibold">Настройки бота</h1>
                  <p className="text-sm text-muted-foreground">
                    Включайте и выключайте разделы главного меню бота. Изменения
                    сохраняются локально в `bot_service` и применяются сразу.
                  </p>
                </div>
                <Button asChild type="button" variant="outline">
                  <Link href="/localization">Открыть локализацию</Link>
                </Button>
              </div>

              <Alert>
                <AlertTitle>Как это работает</AlertTitle>
                <AlertDescription>
                  Если раздел выключен, его кнопка исчезает из главного меню
                  бота, а прямые команды и старые кнопки больше не откроют этот
                  сценарий.
                </AlertDescription>
              </Alert>

              <Card>
                <CardHeader>
                  <CardTitle>Разделы главного меню</CardTitle>
                  <CardDescription>
                    Настройки хранятся в локальном JSON-файле на стороне
                    `bot_service`.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {loading ? (
                    <div className="py-6 text-sm text-muted-foreground">
                      Загружаем текущие настройки бота...
                    </div>
                  ) : (
                    FEATURE_DEFINITIONS.map((feature) => {
                      const enabled = !!draftData.features[feature.key]?.enabled
                      return (
                        <div
                          key={feature.key}
                          className="flex flex-col gap-4 rounded-lg border p-4 sm:flex-row sm:items-start sm:justify-between"
                        >
                          <div className="space-y-1 pr-0 sm:pr-6">
                            <div className="font-medium">{feature.title}</div>
                            <p className="text-sm text-muted-foreground">
                              {feature.description}
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="min-w-[84px] text-right text-sm text-muted-foreground">
                              {enabled ? "Включено" : "Выключено"}
                            </span>
                            <Switch
                              checked={enabled}
                              onCheckedChange={(checked) =>
                                handleToggle(feature.key, checked)
                              }
                              disabled={saving}
                            />
                          </div>
                        </div>
                      )
                    })
                  )}
                </CardContent>
                <CardFooter className="justify-end gap-2 border-t">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={loadSettings}
                    disabled={loading || saving}
                  >
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
                  <Button
                    type="button"
                    onClick={handleSave}
                    disabled={!hasChanges || loading || saving}
                  >
                    {saving ? "Сохранение..." : "Сохранить"}
                  </Button>
                </CardFooter>
              </Card>
            </div>
          )}
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
