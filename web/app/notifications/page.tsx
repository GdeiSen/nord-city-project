"use client"

import { useState } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { IconBell, IconSettings, IconCheck, IconX } from "@tabler/icons-react"
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { PageHeader } from "@/components/page-header"

type Notification = {
  id: number
  title: string
  description: string
  time: string
  read: boolean
}

/**
 * Notifications page component for system-wide notification management
 * 
 * @returns {JSX.Element} Notifications management interface
 */
export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([
    { id: 1, title: 'New Ticket', description: 'New service ticket created', time: '2 hours ago', read: false },
    { id: 2, title: 'Feedback Received', description: 'New user feedback', time: '1 day ago', read: true },
  ])

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    toast('All notifications marked as read', {
      description: 'All notifications have been marked as read.',
    })
  }

  const markRead = (id: number) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))
    toast('Notification marked as read', {
      description: 'This notification has been marked as read.',
    })
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Уведомления"
            description="Управление системными уведомлениями"
            buttonText="Прочитать все"
            onButtonClick={markAllRead}
            buttonIcon={<IconCheck className="h-4 w-4 mr-2" />}
          />

          <Card>
            <CardHeader>
              <CardTitle>Список уведомлений</CardTitle>
            </CardHeader>
            <CardContent>
              {notifications.length === 0 ? (
                <div className="text-center py-8">
                  <IconBell className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold mb-2">Нет новых уведомлений</h3>
                </div>
              ) : (
                <div className="space-y-4">
                  {notifications.map(notif => (
                    <div key={notif.id} className="flex items-start space-x-4 p-4 border rounded-md">
                      <Avatar>
                        <AvatarFallback><IconBell /></AvatarFallback>
                      </Avatar>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium">{notif.title}</h4>
                          <span className="text-sm text-muted-foreground">{notif.time}</span>
                        </div>
                        <p className="text-sm text-muted-foreground">{notif.description}</p>
                      </div>
                      {!notif.read && (
                        <Button variant="ghost" size="sm" onClick={() => markRead(notif.id)}>
                          <IconCheck className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
      <Toaster />
    </>
  )
} 