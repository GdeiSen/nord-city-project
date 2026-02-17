"use client"

import { usePathname } from "next/navigation"
import { useAuthCheck } from "@/hooks"

const PUBLIC_ROUTES = ["/login"]

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { checked, authorized } = useAuthCheck({ pathname, publicRoutes: PUBLIC_ROUTES })

  if (PUBLIC_ROUTES.includes(pathname)) {
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
