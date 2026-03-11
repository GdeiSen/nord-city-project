"use client"

import { usePathname } from "next/navigation"
import { useAuthCheck } from "@/hooks"

const PUBLIC_ROUTES = ["/login"]
const EXTRA_PUBLIC_ROUTES = ["/access-restricted"]

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const publicRoutes = [...PUBLIC_ROUTES, ...EXTRA_PUBLIC_ROUTES]
  const { checked, authorized } = useAuthCheck({ pathname, publicRoutes })

  if (publicRoutes.includes(pathname)) {
    return <>{children}</>
  }

  if (!checked || !authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return <>{children}</>
}
