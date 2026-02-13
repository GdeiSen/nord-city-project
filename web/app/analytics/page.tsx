"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IconChartBar, IconTrendingUp, IconUsers, IconTicket, IconBuildingSkyscraper } from "@tabler/icons-react"
import { serviceTicketApi, userApi, feedbackApi, rentalSpaceApi } from '@/lib/api'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { PageHeader } from "@/components/page-header"
import { ChartAdvanced } from "@/components/chart-advanced"

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<any>({})
  const [chartData, setChartData] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      const [tickets, users, feedbacks, spaces] = await Promise.all([
        serviceTicketApi.getAll(),
        userApi.getAll(),
        feedbackApi.getAll(),
        rentalSpaceApi.getAll(),
      ])

      // Calculate stats
      const completedTickets = tickets.filter(t => t.status === 'COMPLETED')
      const averageResolutionTime = completedTickets.length > 0 
        ? (completedTickets.reduce((sum, t) => sum + (new Date(t.updated_at).getTime() - new Date(t.created_at).getTime()), 0) / completedTickets.length / 3600000).toFixed(1) + ' ч'
        : '0 ч'

      const satisfactionRating = feedbacks.length > 0
        ? (feedbacks.reduce((sum, f) => sum + (parseFloat(f.answer) || 0), 0) / feedbacks.length).toFixed(1) + '/5'
        : '0/5'

      const occupancy = spaces.length > 0 ? ((spaces.filter(s => s.status !== 'FREE').length / spaces.length) * 100).toFixed(1) + '%' : '0%'

      // Monthly tickets for chart
      const monthlyTickets = tickets.reduce((acc, t) => {
        const month = new Date(t.created_at).toLocaleString('default', { month: 'short', year: 'numeric' })
        acc[month] = (acc[month] || 0) + 1
        return acc
      }, {} as Record<string, number>)
      const chartData = Object.entries(monthlyTickets).map(([month, count]) => ({ month, count })).sort((a, b) => new Date(a.month).getTime() - new Date(b.month).getTime())

      setAnalytics({
        userCount: users.length,
        resolutionTime: averageResolutionTime,
        occupancy,
        satisfaction: satisfactionRating,
      })
      setChartData(chartData)
    } catch (error) {
      toast.error('Failed to fetch analytics')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [])

  if (loading) return <div className="flex justify-center items-center h-screen">Loading...</div>

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Аналитика"
            description="Анализ данных и отчеты по работе бизнес-центра"
            buttonText="Обновить данные"
            onButtonClick={fetchAnalytics}
            buttonIcon={<IconTrendingUp className="h-4 w-4 mr-2" />}
          />

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-sm font-medium">Всего пользователей</CardTitle>
                <IconUsers className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analytics.userCount}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-sm font-medium">Время решения заявок</CardTitle>
                <IconTicket className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analytics.resolutionTime}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-sm font-medium">Загрузка помещений</CardTitle>
                <IconBuildingSkyscraper className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analytics.occupancy}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
                <CardTitle className="text-sm font-medium">Рейтинг удовлетворенности</CardTitle>
                <IconTrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{analytics.satisfaction}</div>
              </CardContent>
            </Card>
          </div>
          <ChartAdvanced />
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
} 