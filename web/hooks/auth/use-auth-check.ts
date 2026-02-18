"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { isAuthenticated, getToken, logout } from "@/lib/auth"
import { authApi } from "@/lib/api"

const DEFAULT_PUBLIC_ROUTES = ["/login"]

export interface UseAuthCheckOptions {
  pathname: string
  publicRoutes?: string[]
}

export interface UseAuthCheckReturn {
  checked: boolean
  authorized: boolean
}

export function useAuthCheck(options: UseAuthCheckOptions): UseAuthCheckReturn {
  const { pathname, publicRoutes = DEFAULT_PUBLIC_ROUTES } = options
  const router = useRouter()
  const [checked, setChecked] = useState(false)
  const [authorized, setAuthorized] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      if (publicRoutes.includes(pathname)) {
        setAuthorized(true)
        setChecked(true)
        return
      }

      if (!isAuthenticated()) {
        router.replace("/login")
        return
      }

      const token = getToken()
      if (!token) {
        router.replace("/login")
        return
      }

      try {
        const result = await authApi.validateToken(token)
        if (result.valid) {
          setAuthorized(true)
        } else {
          logout()
          router.replace("/login")
        }
      } catch {
        setAuthorized(true)
      }

      setChecked(true)
    }

    checkAuth()
  }, [pathname, router, publicRoutes])

  return { checked, authorized }
}
