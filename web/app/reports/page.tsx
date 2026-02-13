"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { IconReportAnalytics, IconDownload, IconCalendar, IconFileExport } from "@tabler/icons-react"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { PageHeader } from "@/components/page-header"

export default function ReportsPage() {
  const [reportType, setReportType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const handleGenerate = () => {
    // Mock report generation
    toast.success(`Report ${reportType} generated for ${dateFrom} to ${dateTo}`)
    // Implement actual generation and download
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Отчеты"
            description="Генерация и управление отчетами"
          />

          <Card>
            <CardHeader>
              <CardTitle>Генерация отчета</CardTitle>
              <CardDescription>Выберите параметры для отчета</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="reportType">Тип отчета</Label>
                <Select value={reportType} onValueChange={setReportType}>
                  <SelectTrigger id="reportType">
                    <SelectValue placeholder="Выберите тип" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tickets">Заявки</SelectItem>
                    <SelectItem value="feedbacks">Отзывы</SelectItem>
                    <SelectItem value="occupancy">Загрузка</SelectItem>
                    <SelectItem value="users">Пользователи</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="dateFrom">С даты</Label>
                  <Input id="dateFrom" type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dateTo">По дату</Label>
                  <Input id="dateTo" type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
                </div>
              </div>
              <Button onClick={handleGenerate}>
                <IconFileExport className="h-4 w-4 mr-2" />
                Сгенерировать отчет
              </Button>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
} 