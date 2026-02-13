"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Toggle } from "@/components/ui/toggle"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { IconSettings, IconDeviceFloppy, IconRefresh, IconShield, IconBell, IconPalette } from "@tabler/icons-react"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { useState } from "react"
import { PageHeader } from "@/components/page-header"

/**
 * Settings page component for system configuration
 * 
 * @returns {JSX.Element} System settings and configuration interface
 */
export default function SettingsPage() {
  const [notifications, setNotifications] = useState(true)
  const [theme, setTheme] = useState('light')

  const handleSave = () => {
    // Save settings
    toast.success('Settings saved', { description: 'Your settings have been saved.' })
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Настройки"
            description="Конфигурация системы управления бизнес-центром"
            buttonText="Сохранить"
            onButtonClick={handleSave}
            buttonIcon={<IconDeviceFloppy className="h-4 w-4 mr-2" />}
          />

          <Card>
            <CardHeader>
              <CardTitle>Общие настройки</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="text-base">Уведомления</Label>
                  <p className="text-sm text-muted-foreground">Получать push-уведомления</p>
                </div>
                <Toggle pressed={notifications} onPressedChange={setNotifications} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="theme">Тема</Label>
                <Select value={theme} onValueChange={setTheme}>
                  <SelectTrigger id="theme">
                    <SelectValue placeholder="Выберите тему" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="light">Светлая</SelectItem>
                    <SelectItem value="dark">Темная</SelectItem>
                    <SelectItem value="system">Системная</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
    </>
  )
} 