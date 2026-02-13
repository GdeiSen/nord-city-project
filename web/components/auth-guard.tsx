"use client"

import { useEffect, useState } from "react"
import { useRouter, usePathname } from "next/navigation"
import { isAuthenticated, getToken, logout } from "@/lib/auth"
import { authApi } from "@/lib/api"

const PUBLIC_ROUTES = ["/login"]

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [checked, setChecked] = useState(false)
  const [authorized, setAuthorized] = useState(false)

  useEffect(() => {
    const checkAuth = async () => {
      // Public routes don't require authentication
      if (PUBLIC_ROUTES.includes(pathname)) {
        setAuthorized(true)
        setChecked(true)
        return
      }

      // No token -> redirect to login
      if (!isAuthenticated()) {
        router.replace("/login")
        return
      }

      // Validate token with backend
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
          // Token expired or invalid
          logout()
          router.replace("/login")
        }
      } catch {
        // Network error -- allow access with existing token
        // (offline-first approach; backend will reject invalid tokens on API calls)
        setAuthorized(true)
      }

      setChecked(true)
    }

    checkAuth()
  }, [pathname, router])

  // Public routes render immediately
  if (PUBLIC_ROUTES.includes(pathname)) {
    return <>{children}</>
  }

  // While checking auth, show nothing (prevents flash of protected content)
  if (!checked || !authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return <>{children}</>
}
