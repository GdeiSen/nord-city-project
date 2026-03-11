"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IconUsers, IconTicket, IconMessageCircle, IconBuildingSkyscraper, IconRefresh } from "@tabler/icons-react"
import { DashboardStats } from '@/types'
import { serviceTicketApi, feedbackApi, rentalObjectApi, rentalSpaceApi, userApi } from '@/lib/api'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { useLoading } from "@/hooks"
import dynamic from "next/dynamic"
import { PageHeader } from "@/components/page-header"
import { getUser } from "@/lib/auth"

const DashboardChart = dynamic(
  () => import("@/components/chart").then((m) => m.DashboardChart),
  { ssr: false }
)

function getTimeGreeting(now: Date): string {
  const hour = now.getHours()
  if (hour >= 5 && hour < 12) return "Доброе утро"
  if (hour >= 12 && hour < 17) return "Добрый день"
  if (hour >= 17 && hour < 23) return "Добрый вечер"
  return "Доброй ночи"
}

function isSameLocalDate(value: string | undefined, today: Date): boolean {
  if (!value) return false
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return false
  return (
    parsed.getFullYear() === today.getFullYear()
    && parsed.getMonth() === today.getMonth()
    && parsed.getDate() === today.getDate()
  )
}

function pluralizeRu(count: number, one: string, few: string, many: string): string {
  const mod10 = count % 10
  const mod100 = count % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}

function resolveDashboardUserName(): string {
  const user = getUser()
  if (user?.first_name?.trim()) return user.first_name.trim()
  if (user?.username?.trim()) return user.username.trim()
  return "Администратор"
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    total_users: 0,
    total_tickets: 0,
    pending_tickets: 0,
    completed_tickets: 0,
    total_feedbacks: 0,
    total_objects: 0,
    total_spaces: 0,
    available_spaces: 0,
  })
  const [userName, setUserName] = useState("Администратор")
  const [timeGreeting, setTimeGreeting] = useState("Здравствуйте")
  const [dailySummary, setDailySummary] = useState("Сводка за сегодня обновляется...")
  const { loading, withLoading } = useLoading(true)

  const fetchStats = async () => {
    await withLoading(async () => {
      const [users, tickets, feedbacks, objects, spaces] = await Promise.all([
        userApi.getAll(),
        serviceTicketApi.getAll(),
        feedbackApi.getAll(),
        rentalObjectApi.getAll(),
        rentalSpaceApi.getAll(),
      ])

      setStats({
        total_users: users.length,
        total_tickets: tickets.length,
        pending_tickets: tickets.filter(t => ['NEW', 'ACCEPTED', 'ASSIGNED', 'IN_PROGRESS'].includes(t.status)).length,
        completed_tickets: tickets.filter(t => t.status === 'COMPLETED').length,
        total_feedbacks: feedbacks.length,
        total_objects: objects.length,
        total_spaces: spaces.length,
        available_spaces: spaces.filter(s => s.status === 'FREE').length,
      })

      const today = new Date()
      const newTicketsToday = tickets.filter((ticket) => isSameLocalDate(ticket.created_at, today)).length
      const completedTicketsToday = tickets.filter(
        (ticket) => ticket.status === 'COMPLETED' && isSameLocalDate(ticket.updated_at || ticket.created_at, today)
      ).length
      const feedbacksToday = feedbacks.filter((feedback) => isSameLocalDate(feedback.created_at, today)).length
      const todayLabel = today.toLocaleDateString("ru-RU", { day: "2-digit", month: "long" })
      const freeSpaces = spaces.filter((space) => space.status === "FREE").length

      setDailySummary(
        `На ${todayLabel} поступило ${newTicketsToday} ${pluralizeRu(newTicketsToday, "новая заявка", "новые заявки", "новых заявок")}, `
        + `завершено ${completedTicketsToday} ${pluralizeRu(completedTicketsToday, "заявка", "заявки", "заявок")}, `
        + `получено ${feedbacksToday} ${pluralizeRu(feedbacksToday, "отзыв", "отзыва", "отзывов")}. `
        + `Сейчас свободно ${freeSpaces} из ${spaces.length} ${pluralizeRu(spaces.length, "помещения", "помещений", "помещений")}.`
      )
    }).catch((error) => {
      toast.error('Failed to fetch dashboard stats')
      console.error(error)
    })
  }

  useEffect(() => {
    setUserName(resolveDashboardUserName())
    const updateGreeting = () => setTimeGreeting(getTimeGreeting(new Date()))
    updateGreeting()
    const timer = window.setInterval(updateGreeting, 60_000)
    fetchStats()
    return () => window.clearInterval(timer)
  }, [])

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <Card>
            <CardContent className="pt-6 space-y-2">
              <h1 className="text-2xl font-semibold tracking-tight">{timeGreeting}, {userName}!</h1>
              <p className="text-sm text-muted-foreground">{dailySummary}</p>
            </CardContent>
          </Card>

          <PageHeader
            title="Дашборд"
            description="Обзор ключевых метрик системы"
            buttonText="Обновить данные"
            onButtonClick={fetchStats}
            buttonIcon={<IconRefresh className="h-4 w-4" />}
          />

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего пользователей</CardTitle>
                <IconUsers className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_users}</div>
                <p className="text-xs text-muted-foreground">активных аккаунтов</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего заявок</CardTitle>
                <IconTicket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_tickets}</div>
                <p className="text-xs text-muted-foreground">на обслуживание</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Заявок в работе</CardTitle>
                <IconTicket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.pending_tickets}</div>
                <p className="text-xs text-muted-foreground">требуют внимания</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Завершенных заявок</CardTitle>
                <IconTicket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.completed_tickets}</div>
                <p className="text-xs text-muted-foreground">успешно обработано</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего отзывов</CardTitle>
                <IconMessageCircle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_feedbacks}</div>
                <p className="text-xs text-muted-foreground">от пользователей</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего объектов</CardTitle>
                <IconBuildingSkyscraper className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_objects}</div>
                <p className="text-xs text-muted-foreground">бизнес-центров</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего помещений</CardTitle>
                <IconBuildingSkyscraper className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_spaces}</div>
                <p className="text-xs text-muted-foreground">для аренды</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Свободных помещений</CardTitle>
                <IconBuildingSkyscraper className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.available_spaces}</div>
                <p className="text-xs text-muted-foreground">доступно сейчас</p>
              </CardContent>
            </Card>
          </div>

          <DashboardChart className="mt-6" />
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
