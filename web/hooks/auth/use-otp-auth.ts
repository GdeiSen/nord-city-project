"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { authApi } from "@/lib/api"
import { setToken, setUser } from "@/lib/auth"
import { formatApiError } from "@/lib/format-api-error"

type AuthStep = "enter_id" | "enter_otp"

export interface UseOtpAuthOptions {
  onSuccess?: () => void
}

export interface UseOtpAuthReturn {
  step: AuthStep
  setStep: (step: AuthStep) => void
  identifier: string
  setIdentifier: (v: string) => void
  resolvedUserId: number | null
  otpCode: string
  setOtpCode: (v: string) => void
  errorInfo: { title: string; details: string } | null
  setErrorInfo: (v: { title: string; details: string } | null) => void
  loading: boolean
  handleRequestOtp: () => Promise<void>
  handleVerifyOtp: (code: string) => Promise<void>
  handleOtpChange: (value: string) => void
}

export function useOtpAuth(options?: UseOtpAuthOptions): UseOtpAuthReturn {
  const { onSuccess } = options ?? {}
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
      setErrorInfo(formatApiError(err))
    } finally {
      setLoading(false)
    }
  }, [identifier])

  const handleVerifyOtp = useCallback(
    async (code: string) => {
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
          onSuccess?.() ?? router.push("/")
        }
      } catch (err: unknown) {
        setErrorInfo(formatApiError(err))
        setOtpCode("")
      } finally {
        setLoading(false)
      }
    },
    [resolvedUserId, router, onSuccess]
  )

  const handleOtpChange = useCallback(
    (value: string) => {
      setOtpCode(value)
      setErrorInfo(null)
      if (value.length === 6) {
        handleVerifyOtp(value)
      }
    },
    [handleVerifyOtp]
  )

  return {
    step,
    setStep,
    identifier,
    setIdentifier,
    resolvedUserId,
    otpCode,
    setOtpCode,
    errorInfo,
    setErrorInfo,
    loading,
    handleRequestOtp,
    handleVerifyOtp,
    handleOtpChange,
  }
}
