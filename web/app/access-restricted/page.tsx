"use client"

import { useRouter } from "next/navigation"
import { IconLock } from "@tabler/icons-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { logout } from "@/lib/auth"

export default function AccessRestrictedPage() {
  const router = useRouter()

  const handleGoToLogin = () => {
    logout()
    router.replace("/login")
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="space-y-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <IconLock className="h-5 w-5" />
          </div>
          <CardTitle>Access Restricted</CardTitle>
          <CardDescription>
            Ваш доступ к панели управления ограничен. Учетная запись удалена или у вас больше нет роли администратора.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-end">
          <Button type="button" onClick={handleGoToLogin}>
            На страницу входа
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
