"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { getToken, getUser, isAuthenticated, logout, setUser } from "@/lib/auth"
import { authApi } from "@/lib/api"

const DEFAULT_PUBLIC_ROUTES = ["/login", "/access-restricted"]

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
        setChecked(true)
        return
      }

      const token = getToken()
      if (!token) {
        router.replace("/login")
        setChecked(true)
        return
      }

      try {
        const result = await authApi.validateToken(token)
        if (result.valid) {
          const currentUser = getUser()
          if (result.user_id != null) {
            const nextAccess = {
              roles: result.roles ?? [],
              permissions: result.permissions ?? [],
              is_super_admin: !!result.is_super_admin,
            }
            if (currentUser) {
              if (
                currentUser.id !== result.user_id ||
                JSON.stringify(currentUser.roles ?? []) !== JSON.stringify(nextAccess.roles) ||
                JSON.stringify(currentUser.permissions ?? []) !== JSON.stringify(nextAccess.permissions) ||
                !!currentUser.is_super_admin !== nextAccess.is_super_admin
              ) {
                setUser({ ...currentUser, id: result.user_id, ...nextAccess })
              }
            } else {
              setUser({ id: result.user_id, ...nextAccess })
            }
          }
          setAuthorized(true)
          setChecked(true)
          return
        } else {
          logout()
          if (result.reason === "access_restricted") {
            router.replace("/access-restricted")
          } else {
            router.replace("/login")
          }
        }
      } catch {
        logout()
        router.replace("/login")
      }

      setChecked(true)
    }

    checkAuth()
  }, [pathname, router, publicRoutes])

  return { checked, authorized }
}
