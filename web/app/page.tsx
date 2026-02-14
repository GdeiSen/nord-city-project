"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { IconUsers, IconTicket, IconMessageCircle, IconBuildingSkyscraper, IconTrendingUp, IconEye, IconRefresh } from "@tabler/icons-react"
import { DashboardStats } from '@/types'
import { serviceTicketApi, feedbackApi, rentalObjectApi, rentalSpaceApi, userApi } from '@/lib/api'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { LoadingWrapper } from "@/components/ui/loading-wrapper"
import { useLoading } from "@/hooks/use-loading"
import { PageHeader } from "@/components/page-header"

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
        pending_tickets: tickets.filter(t => ['NEW', 'ACCEPTED', 'ASSIGNED'].includes(t.status)).length,
        completed_tickets: tickets.filter(t => t.status === 'COMPLETED').length,
        total_feedbacks: feedbacks.length,
        total_objects: objects.length,
        total_spaces: spaces.length,
        available_spaces: spaces.filter(s => s.status === 'FREE').length,
      })
    }).catch((error) => {
      toast.error('Failed to fetch dashboard stats')
      console.error(error)
    })
  }

  useEffect(() => {
    fetchStats()
  }, [])

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Дашборд"
            description="Обзор ключевых метрик системы"
            buttonText="Обновить данные"
            onButtonClick={fetchStats}
            buttonIcon={<IconRefresh className="h-4 w-4 mr-2" />}
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
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
}
