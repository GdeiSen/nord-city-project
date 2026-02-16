"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
  InputOTPSeparator,
} from "@/components/ui/input-otp"
import { authApi } from "@/lib/api"
import { setToken, setUser } from "@/lib/auth"
import { IconBrandTelegram, IconLoader2, IconAlertCircle } from "@tabler/icons-react"

type AuthStep = "enter_id" | "enter_otp"

function formatError(err: unknown): { title: string; details: string } {
  const e = err as Error & { status?: number; details?: unknown }
  const title = e?.message || "Произошла ошибка"
  const parts: string[] = []

  if (e?.status) {
    parts.push(`Код ответа: ${e.status}`)
  }
  const details = e?.details
  if (Array.isArray(details)) {
    details.forEach((item: { loc?: string[]; msg?: string }) => {
      const loc = Array.isArray(item.loc) ? item.loc.join(" → ") : ""
      const msg = item.msg || ""
      if (msg) parts.push(loc ? `${loc}: ${msg}` : msg)
    })
  } else if (typeof details === "object" && details !== null) {
    const extra = (details as Record<string, string>).msg || JSON.stringify(details)
    if (extra && extra !== title) parts.push(extra)
  } else if (typeof details === "string" && details !== title) {
    parts.push(details)
  }

  return { title, details: parts.length ? parts.join("\n") : "" }
}

export default function LoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<AuthStep>("enter_id")
  const [identifier, setIdentifier] = useState("")
  const [resolvedUserId, setResolvedUserId] = useState<number | null>(null)
  const [otpCode, setOtpCode] = useState("")
  const [errorInfo, setErrorInfo] = useState<{ title: string; details: string } | null>(null)
  const [loading, setLoading] = useState(false)

  const handleRequestOtp = useCallback(async () => {
    setErrorInfo(null)

    const trimmed = identifier.trim()
    if (!trimmed) {
      setErrorInfo({ title: "Ошибка ввода", details: "Введите Telegram ID или @username." })
      return
    }

    setLoading(true)
    try {
      const idNum = parseInt(trimmed, 10)
      const isNumeric = !isNaN(idNum) && String(idNum) === trimmed
      const params = isNumeric ? { userId: idNum } : { username: trimmed }
      const result = await authApi.requestOtp(params)
      if (result.success) {
        setResolvedUserId(result.user_id ?? (isNumeric ? idNum : null))
        setStep("enter_otp")
      }
    } catch (err: unknown) {
      setErrorInfo(formatError(err))
    } finally {
      setLoading(false)
    }
  }, [identifier])

  const handleVerifyOtp = useCallback(async (code: string) => {
    setErrorInfo(null)

    if (code.length !== 6) return
    if (resolvedUserId == null) {
      setErrorInfo({
        title: "Ошибка сессии",
        details: "Сессия истекла. Запросите код повторно.",
      })
      return
    }

    setLoading(true)
    try {
      const result = await authApi.verifyOtp(resolvedUserId, code)

      if (result.success && result.access_token) {
        setToken(result.access_token)
        if (result.user) {
          setUser(result.user)
        }
        router.push("/")
      }
    } catch (err: unknown) {
      setErrorInfo(formatError(err))
      setOtpCode("")
    } finally {
      setLoading(false)
    }
  }, [resolvedUserId, router])

  const handleOtpChange = useCallback((value: string) => {
    setOtpCode(value)
    setErrorInfo(null)
    if (value.length === 6) {
      handleVerifyOtp(value)
    }
  }, [handleVerifyOtp])

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
      <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold tracking-tight">Nord City</h1>
          <p className="text-sm text-muted-foreground">Панель управления</p>
        </div>
        {/* Login Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-xl">Авторизация</CardTitle>
            <CardDescription>
              {step === "enter_id"
                ? "Введите ваш Telegram ID или @username для получения кода подтверждения"
                : "Мы отправили 6-значный код в ваш Telegram. Введите его ниже для входа."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {step === "enter_id" ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="telegram-id">Telegram ID или @username</Label>
                <div className="relative">
                  <IconBrandTelegram className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="telegram-id"
                    type="text"
                    value={identifier}
                    onChange={(e) => {
                      setIdentifier(e.target.value)
                      setErrorInfo(null)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRequestOtp()
                    }}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
              </div>

              {errorInfo && (
                <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3">
                  <div className="flex gap-2">
                    <IconAlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                    <div className="space-y-1 text-sm">
                      <p className="font-medium text-destructive">{errorInfo.title}</p>
                      {errorInfo.details && (
                        <pre className="whitespace-pre-wrap break-words text-destructive/90 font-sans text-xs">
                          {errorInfo.details}
                        </pre>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <Button
                className="w-full"
                onClick={handleRequestOtp}
                disabled={loading || !identifier.trim()}
              >
                {loading ? (
                  <>
                    <IconLoader2 className="mr-2 h-4 w-4 animate-spin" />
                    Отправка...
                  </>
                ) : (
                  <>
                    Получить код
                  </>
                )}
              </Button>

              <p className="text-center text-xs text-muted-foreground">
                Код будет отправлен в ваш Telegram от бота Nord City.
                <br />
                Доступ предоставляется только администраторам.
              </p>
            </div>
            ) : (
            <div className="space-y-4">
              <div className="flex flex-col items-center gap-4">
                <InputOTP
              maxLength={6}
              value={otpCode}
              onChange={handleOtpChange}
              disabled={loading}
            >
              <InputOTPGroup>
                <InputOTPSlot index={0} />
                <InputOTPSlot index={1} />
                <InputOTPSlot index={2} />
              </InputOTPGroup>
              <InputOTPSeparator />
              <InputOTPGroup>
                <InputOTPSlot index={3} />
                <InputOTPSlot index={4} />
                <InputOTPSlot index={5} />
              </InputOTPGroup>
            </InputOTP>

            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <IconLoader2 className="h-4 w-4 animate-spin" />
                Проверка кода...
              </div>
            )}

            {errorInfo && (
              <div className="w-full rounded-md border border-destructive/50 bg-destructive/10 p-3">
                <div className="flex gap-2">
                  <IconAlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                  <div className="flex-1 space-y-1 text-sm">
                    <p className="font-medium text-destructive">{errorInfo.title}</p>
                    {errorInfo.details && (
                      <pre className="whitespace-pre-wrap break-words text-destructive/90 font-sans text-xs">
                        {errorInfo.details}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            )}

                <p className="text-xs text-muted-foreground text-center">
                  Код действителен 5 минут.
                  <br />
                  <button
                    type="button"
                    onClick={() => {
                      setOtpCode("")
                      setErrorInfo(null)
                      handleRequestOtp()
                    }}
                    className="text-primary underline-offset-4 hover:underline disabled:opacity-50"
                    disabled={loading}
                  >
                    Отправить код повторно
                  </button>
                </p>
              </div>
            </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
