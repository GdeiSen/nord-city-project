"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { format, parse, parseISO, startOfDay, isBefore, isToday } from "date-fns"
import { ru } from "date-fns/locale"
import { IconCalendar } from "@tabler/icons-react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { GuestParkingRequest, User } from "@/types"
import { guestParkingApi, userApi } from "@/lib/api"
import { EntityPicker } from "@/components/entity-picker"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useLoading, useRouteId } from "@/hooks"
import { toast } from "sonner"
import { Toaster } from "@/components/ui/sonner"

/** Парсит "HH:MM" в [часы, минуты] для отображения */
function parseTime(timeStr: string): [string, string] {
  const parts = (timeStr || "09:00").split(":")
  const h = (parts[0] ?? "").replace(/\D/g, "").slice(0, 2)
  const m = (parts[1] ?? "").replace(/\D/g, "").slice(0, 2)
  return [h, m]
}

/** Собирает "HH:MM" для сохранения. Пустые значения → 09 и 00. */
function buildTimeString(hourStr: string, minuteStr: string): string {
  const h = hourStr.replace(/\D/g, "").slice(0, 2)
  const m = minuteStr.replace(/\D/g, "").slice(0, 2)
  const hn = parseInt(h, 10)
  const mn = parseInt(m, 10)
  const hVal = h ? Math.min(23, Math.max(0, isNaN(hn) ? 9 : hn)) : 9
  const mVal = m ? Math.min(59, Math.max(0, isNaN(mn) ? 0 : mn)) : 0
  return `${String(hVal).padStart(2, "0")}:${String(mVal).padStart(2, "0")}`
}

function toDateString(d: Date): string {
  return format(d, "yyyy-MM-dd")
}

function parseDateInput(input: string): Date | null {
  const s = input.trim()
  if (!s) return null
  const formats = ["dd.MM.yyyy", "yyyy-MM-dd", "d.M.yyyy", "dd.MM.yy"]
  for (const fmt of formats) {
    try {
      const d = parse(s, fmt, new Date(), { locale: ru })
      if (!isNaN(d.getTime())) return d
    } catch {
      /* skip */
    }
  }
  const parsed = new Date(s)
  return !isNaN(parsed.getTime()) ? parsed : null
}

/** Форматирует datetime в date и time для формы */
function splitDateTime(iso: string | undefined): { date: string; time: string } {
  if (!iso) {
    const now = new Date()
    return {
      date: toDateString(now),
      time: "09:00",
    }
  }
  const d = new Date(iso)
  return {
    date: toDateString(d),
    time: `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`,
  }
}

function toISOString(date: string, time: string): string {
  return `${date}T${time}:00`
}

/** Проверка номера Беларуси: +375XXXXXXXXX, 80XXXXXXXXX, 8 0XX XXX XX XX, с пробелами/скобками/тире */
function isValidBelarusPhone(text: string): boolean {
  const s = (text || "").trim()
  if (!s) return false
  return /^[\s\-\(\)]*(?:\+375|80|8\s*0)([\s\-\(\)]*\d){9}[\s\-\(\)]*$/.test(s)
}

/** Сообщение об ошибке для номера телефона или null если валиден */
function getPhoneValidationError(phone: string, required: boolean): string | null {
  const trimmed = (phone || "").trim()
  if (!trimmed) return required ? "Укажите номер телефона" : null
  if (!isValidBelarusPhone(trimmed)) return "Некорректный номер. Формат: +375XXXXXXXXX"
  return null
}

/** Валидация: дата и время не в прошлом. Гостевая парковка 9:00–19:00. */
function validateArrivalDateTime(dateStr: string, timeStr: string): string | null {
  const parsedDate = parseDateInput(dateStr) || (dateStr.match(/^\d{4}-\d{2}-\d{2}$/) ? parseISO(dateStr) : null)
  if (!parsedDate || isNaN(parsedDate.getTime())) return "Укажите корректную дату"
  if (isBefore(parsedDate, startOfDay(new Date()))) return "Указанная дата уже прошла. Выберите сегодня или дату в будущем."
  const [h, m] = timeStr.split(":").map(Number)
  if (h < 9 || h > 19 || (h === 19 && m > 0)) return "Время должно быть с 9:00 до 19:00"
  const arrival = new Date(parsedDate)
  arrival.setHours(h, m, 0, 0)
  if (isBefore(arrival, new Date())) return "Указанные дата и время уже прошли. Выберите другое время."
  return null
}

export default function GuestParkingEditPage() {
  const router = useRouter()
  const { id: reqId, isEdit } = useRouteId({ paramKey: "id", parseMode: "number" })

  const { loading, withLoading } = useLoading(true)
  const [users, setUsers] = useState<User[]>([])
  const [formData, setFormData] = useState<{
    user_id: number | null
    arrival_date: string
    arrival_time: string
    license_plate: string
    car_make_color: string
    driver_phone: string
    tenant_phone: string
  }>({
    user_id: null,
    arrival_date: "",
    arrival_time: "09:00",
    license_plate: "",
    car_make_color: "",
    driver_phone: "",
    tenant_phone: "",
  })
  const [saving, setSaving] = useState(false)
  const [dateInputDisplay, setDateInputDisplay] = useState("")
  const [hourDisplay, setHourDisplay] = useState("09")
  const [minuteDisplay, setMinuteDisplay] = useState("00")
  const [driverPhoneError, setDriverPhoneError] = useState("")
  const [tenantPhoneError, setTenantPhoneError] = useState("")

  useEffect(() => {
    const load = async () => {
      const allUsers = await userApi.getAll()
      setUsers(allUsers)
      if (isEdit && reqId) {
        const req = await guestParkingApi.getById(Number(reqId))
        const { date, time } = splitDateTime(req.arrival_date)
        const [h, m] = parseTime(time)
        setFormData({
          user_id: req.user_id,
          arrival_date: date,
          arrival_time: time,
          license_plate: req.license_plate ?? "",
          car_make_color: req.car_make_color ?? "",
          driver_phone: req.driver_phone ?? "",
          tenant_phone: req.tenant_phone ?? "",
        })
        setDateInputDisplay(date ? format(parseISO(date), "dd.MM.yyyy", { locale: ru }) : "")
        setHourDisplay(h || "09")
        setMinuteDisplay(m || "00")
        setDriverPhoneError("")
        setTenantPhoneError("")
      } else {
        const now = new Date()
        const dateStr = toDateString(now)
        setFormData((prev) => ({
          ...prev,
          arrival_date: dateStr,
          arrival_time: "09:00",
        }))
        setDateInputDisplay(format(now, "dd.MM.yyyy", { locale: ru }))
        setHourDisplay("09")
        setMinuteDisplay("00")
        setDriverPhoneError("")
        setTenantPhoneError("")
      }
    }
    withLoading(load).catch((err: any) => {
      toast.error("Не удалось загрузить данные", { description: err?.message })
      if (isEdit) router.push(`/guest-parking/${Number(reqId!)}`)
      else router.push("/guest-parking")
    })
  }, [reqId, isEdit])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    if (!formData.user_id) {
      toast.error("Выберите арендатора")
      return
    }
    if (!formData.license_plate?.trim()) {
      toast.error("Укажите госномер")
      return
    }
    if (!formData.car_make_color?.trim()) {
      toast.error("Укажите марку и цвет автомобиля")
      return
    }
    const driverPhoneError = getPhoneValidationError(formData.driver_phone, true)
    if (driverPhoneError) {
      toast.error(driverPhoneError)
      return
    }
    const tenantPhoneError = getPhoneValidationError(formData.tenant_phone, false)
    if (tenantPhoneError) {
      toast.error(tenantPhoneError)
      return
    }
    const dateTimeError = validateArrivalDateTime(formData.arrival_date, formData.arrival_time)
    if (dateTimeError) {
      toast.error(dateTimeError)
      return
    }
    setSaving(true)
    try {
      const arrivalDate = toISOString(formData.arrival_date, formData.arrival_time)
      if (isEdit && reqId) {
        await guestParkingApi.update(Number(reqId), {
          user_id: formData.user_id,
          arrival_date: arrivalDate,
          license_plate: formData.license_plate.trim(),
          car_make_color: formData.car_make_color.trim(),
          driver_phone: formData.driver_phone.trim(),
          tenant_phone: formData.tenant_phone.trim() || undefined,
        } as any)
        toast.success("Заявка обновлена")
        router.push(`/guest-parking/${Number(reqId)}`)
      } else {
        const created = await guestParkingApi.create({
          user_id: formData.user_id,
          arrival_date: arrivalDate,
          license_plate: formData.license_plate.trim(),
          car_make_color: formData.car_make_color.trim(),
          driver_phone: formData.driver_phone.trim(),
          tenant_phone: formData.tenant_phone.trim() || undefined,
        } as any)
        toast.success("Заявка создана")
        router.push(`/guest-parking/${created.id}`)
      }
    } catch (err: any) {
      toast.error("Не удалось сохранить заявку", { description: err?.message })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!isEdit || !reqId) return
    try {
      await guestParkingApi.delete(Number(reqId))
      toast.success("Заявка удалена")
      router.push("/guest-parking")
    } catch (err: any) {
      toast.error("Не удалось удалить заявку", { description: err?.message })
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
                  <Link href="/guest-parking">Гостевая парковка</Link>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>{isEdit ? `Редактирование #${reqId}` : "Новая заявка"}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <div className="max-w-2xl space-y-6">
            <div>
              <h1 className="text-2xl font-semibold">
                {isEdit ? "Редактирование заявки" : "Создание заявки"}
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                {isEdit ? "Изменение данных заявки. Сообщение в чате администраторов обновится." : "Создайте заявку на гостевую парковку. Уведомление будет отправлено в чат администраторов."}
              </p>
            </div>
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              </div>
            ) : (
              <div className="grid gap-6">
                <div className="space-y-2">
                  <Label>Арендатор</Label>
                  <EntityPicker<User>
                    dataConfig={{
                      data: users,
                      getValue: (u) => u.id,
                      getLabel: (u) => {
                        const name = `${u.last_name ?? ""} ${u.first_name ?? ""}`.trim()
                        return name ? `${name}${u.username ? ` (@${u.username})` : ""}` : (u.username ? `@${u.username}` : `#${u.id}`)
                      },
                    }}
                    value={formData.user_id}
                    onSelect={(u) => setFormData((prev) => ({ ...prev, user_id: u.id }))}
                    placeholder="Выберите арендатора"
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="arrival_date">Дата заезда</Label>
                    <div className="flex gap-1">
                      <Popover>
                        <PopoverTrigger asChild>
                          <Button
                            variant="outline"
                            className="h-9 shrink-0"
                            size="icon"
                            type="button"
                            aria-label="Календарь"
                          >
                            <IconCalendar className="h-4 w-4" />
                          </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-auto p-0" align="start">
                          <Calendar
                            mode="single"
                            locale={ru}
                            selected={formData.arrival_date ? parseISO(formData.arrival_date) : undefined}
                            onSelect={(d) => {
                              if (d) {
                                const dateStr = toDateString(d)
                                setFormData((prev) => ({ ...prev, arrival_date: dateStr }))
                                setDateInputDisplay(format(d, "dd.MM.yyyy", { locale: ru }))
                              }
                            }}
                            disabled={{ before: startOfDay(new Date()) }}
                            initialFocus
                          />
                        </PopoverContent>
                      </Popover>
                      <Input
                        id="arrival_date"
                        placeholder="дд.мм.гггг"
                        value={dateInputDisplay}
                        onChange={(e) => setDateInputDisplay(e.target.value)}
                        onBlur={() => {
                          const d = parseDateInput(dateInputDisplay)
                          if (d) {
                            const dateStr = toDateString(d)
                            setFormData((prev) => ({ ...prev, arrival_date: dateStr }))
                            setDateInputDisplay(format(d, "dd.MM.yyyy", { locale: ru }))
                          }
                        }}
                        className="flex-1"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Время заезда (9:00–19:00)</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        id="arrival_hour"
                        inputMode="numeric"
                        placeholder="09"
                        maxLength={2}
                        value={hourDisplay}
                        onChange={(e) => {
                          const v = e.target.value.replace(/\D/g, "").slice(0, 2)
                          setHourDisplay(v)
                          setFormData((prev) => ({
                            ...prev,
                            arrival_time: buildTimeString(v, minuteDisplay),
                          }))
                        }}
                        onBlur={() => {
                          const normalized = hourDisplay ? String(Math.min(23, Math.max(0, parseInt(hourDisplay, 10) || 9))).padStart(2, "0") : "09"
                          setHourDisplay(normalized)
                          setFormData((prev) => ({ ...prev, arrival_time: buildTimeString(normalized, minuteDisplay) }))
                        }}
                        className="w-14 text-center"
                        aria-label="Часы"
                      />
                      <span className="text-muted-foreground">:</span>
                      <Input
                        id="arrival_minute"
                        inputMode="numeric"
                        placeholder="00"
                        maxLength={2}
                        value={minuteDisplay}
                        onChange={(e) => {
                          const v = e.target.value.replace(/\D/g, "").slice(0, 2)
                          setMinuteDisplay(v)
                          setFormData((prev) => ({
                            ...prev,
                            arrival_time: buildTimeString(hourDisplay, v),
                          }))
                        }}
                        onBlur={() => {
                          const normalized = minuteDisplay ? String(Math.min(59, Math.max(0, parseInt(minuteDisplay, 10) || 0))).padStart(2, "0") : "00"
                          setMinuteDisplay(normalized)
                          setFormData((prev) => ({ ...prev, arrival_time: buildTimeString(hourDisplay, normalized) }))
                        }}
                        className="w-14 text-center"
                        aria-label="Минуты"
                      />
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="license_plate">Госномер</Label>
                  <Input
                    id="license_plate"
                    name="license_plate"
                    value={formData.license_plate}
                    onChange={handleInputChange}
                    placeholder="А123БВ77"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="car_make_color">Марка и цвет автомобиля</Label>
                  <Input
                    id="car_make_color"
                    name="car_make_color"
                    value={formData.car_make_color}
                    onChange={handleInputChange}
                    placeholder="Toyota Corolla, белый"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="driver_phone">Телефон водителя</Label>
                  <Input
                    id="driver_phone"
                    name="driver_phone"
                    type="tel"
                    value={formData.driver_phone}
                    onChange={(e) => {
                      handleInputChange(e)
                      if (getPhoneValidationError(e.target.value, true) === null) setDriverPhoneError("")
                    }}
                    onBlur={(e) => {
                      const err = getPhoneValidationError(e.target.value, true)
                      setDriverPhoneError(err ?? "")
                    }}
                    placeholder="+375291234567"
                    className={driverPhoneError ? "border-destructive" : undefined}
                    aria-invalid={!!driverPhoneError}
                  />
                  {driverPhoneError && (
                    <p className="text-sm text-destructive">{driverPhoneError}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tenant_phone">Телефон арендатора</Label>
                  <Input
                    id="tenant_phone"
                    name="tenant_phone"
                    type="tel"
                    value={formData.tenant_phone}
                    onChange={(e) => {
                      handleInputChange(e)
                      if (getPhoneValidationError(e.target.value, false) === null) setTenantPhoneError("")
                    }}
                    onBlur={(e) => {
                      const err = getPhoneValidationError(e.target.value, false)
                      setTenantPhoneError(err ?? "")
                    }}
                    placeholder="+375291234567"
                    className={tenantPhoneError ? "border-destructive" : undefined}
                    aria-invalid={!!tenantPhoneError}
                  />
                  {tenantPhoneError && (
                    <p className="text-sm text-destructive">{tenantPhoneError}</p>
                  )}
                </div>

                <div className="flex flex-col-reverse sm:flex-row gap-2 sm:justify-end pt-4">
                  {isEdit && (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="outline"
                          className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600 sm:mr-auto"
                        >
                          Удалить
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Удалить эту заявку?</AlertDialogTitle>
                          <AlertDialogDescription>
                            Сообщение в чате администраторов будет удалено.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Отмена</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={handleDelete}
                          >
                            Удалить
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? "Сохранение..." : "Сохранить"}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
