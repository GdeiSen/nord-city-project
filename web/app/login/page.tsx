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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { authApi } from "@/lib/api"
import { setToken, setUser } from "@/lib/auth"
import { IconBrandTelegram, IconShieldLock, IconLoader2 } from "@tabler/icons-react"

type AuthStep = "enter_id" | "enter_otp"

export default function LoginPage() {
  const router = useRouter()
  const [step, setStep] = useState<AuthStep>("enter_id")
  const [userId, setUserId] = useState("")
  const [otpCode, setOtpCode] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [otpDialogOpen, setOtpDialogOpen] = useState(false)

  const handleRequestOtp = useCallback(async () => {
    setError("")

    const id = parseInt(userId.trim(), 10)
    if (!id || isNaN(id)) {
      setError("Введите корректный Telegram ID.")
      return
    }

    setLoading(true)
    try {
      const result = await authApi.requestOtp(id)
      if (result.success) {
        setStep("enter_otp")
        setOtpDialogOpen(true)
      }
    } catch (err: any) {
      const detail = err?.response
        ? (() => { try { return JSON.parse(err.response).detail } catch { return null } })()
        : null
      setError(detail || err?.message || "Ошибка при отправке кода.")
    } finally {
      setLoading(false)
    }
  }, [userId])

  const handleVerifyOtp = useCallback(async (code: string) => {
    setError("")

    if (code.length !== 6) return

    setLoading(true)
    try {
      const id = parseInt(userId.trim(), 10)
      const result = await authApi.verifyOtp(id, code)

      if (result.success && result.access_token) {
        setToken(result.access_token)
        if (result.user) {
          setUser(result.user)
        }
        setOtpDialogOpen(false)
        router.push("/")
      }
    } catch (err: any) {
      const detail = err?.response
        ? (() => { try { return JSON.parse(err.response).detail } catch { return null } })()
        : null
      setError(detail || err?.message || "Неверный код.")
      setOtpCode("")
    } finally {
      setLoading(false)
    }
  }, [userId, router])

  const handleOtpChange = useCallback((value: string) => {
    setOtpCode(value)
    setError("")
    if (value.length === 6) {
      handleVerifyOtp(value)
    }
  }, [handleVerifyOtp])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        {/* Logo / Brand */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <IconShieldLock className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Nord City</h1>
          <p className="text-sm text-muted-foreground">Панель управления</p>
        </div>

        {/* Login Card */}
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-xl">Авторизация</CardTitle>
            <CardDescription>
              Введите ваш Telegram ID для получения кода подтверждения
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="telegram-id">Telegram ID</Label>
                <div className="relative">
                  <IconBrandTelegram className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="telegram-id"
                    type="text"
                    inputMode="numeric"
                    placeholder="Например: 123456789"
                    value={userId}
                    onChange={(e) => {
                      setUserId(e.target.value)
                      setError("")
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleRequestOtp()
                    }}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
              </div>

              {error && step === "enter_id" && (
                <p className="text-sm text-destructive">{error}</p>
              )}

              <Button
                className="w-full"
                onClick={handleRequestOtp}
                disabled={loading || !userId.trim()}
              >
                {loading ? (
                  <>
                    <IconLoader2 className="mr-2 h-4 w-4 animate-spin" />
                    Отправка...
                  </>
                ) : (
                  <>
                    <IconBrandTelegram className="mr-2 h-4 w-4" />
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
          </CardContent>
        </Card>
      </div>

      {/* OTP Verification Dialog */}
      <Dialog open={otpDialogOpen} onOpenChange={setOtpDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">Введите код подтверждения</DialogTitle>
            <DialogDescription className="text-center">
              Мы отправили 6-значный код в ваш Telegram.
              <br />
              Введите его ниже для входа.
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col items-center gap-4 py-4">
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

            {error && step === "enter_otp" && (
              <p className="text-sm text-destructive text-center">{error}</p>
            )}

            <p className="text-xs text-muted-foreground text-center">
              Код действителен 5 минут.
              <br />
              <button
                type="button"
                onClick={() => {
                  setOtpCode("")
                  setError("")
                  handleRequestOtp()
                }}
                className="text-primary underline-offset-4 hover:underline disabled:opacity-50"
                disabled={loading}
              >
                Отправить код повторно
              </button>
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
