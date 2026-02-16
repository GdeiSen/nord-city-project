"use client"

import { usePathname } from "next/navigation"
import { SidebarProvider } from "@/components/ui/sidebar"

const PUBLIC_ROUTES = ["/login"]

export function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isPublicRoute = PUBLIC_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`))

  if (isPublicRoute) {
    return <>{children}</>
  }

  return <SidebarProvider>{children}</SidebarProvider>
}
