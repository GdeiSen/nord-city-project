"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { IconHelp, IconBook, IconHeadphones, IconMail } from "@tabler/icons-react"
import { PageHeader } from "@/components/page-header"

/**
 * Help page component with user support and documentation
 * 
 * @returns {JSX.Element} Help and support interface
 */
export default function HelpPage() {
  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Справка"
            description="Документация и поддержка пользователей"
          />

          <Card>
            <CardHeader>
              <CardTitle>Центр помощи</CardTitle>
              <CardDescription>
                Руководства пользователя и техническая поддержка
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <IconHelp className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Нужна помощь?</h3>
                <p className="text-muted-foreground mb-6">
                  Здесь вы найдете ответы на частые вопросы и сможете связаться с поддержкой
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
                  <Button variant="outline" className="h-16 flex-col">
                    <IconBook className="h-6 w-6 mb-2" />
                    <span>Руководства</span>
                  </Button>
                  <Button variant="outline" className="h-16 flex-col">
                    <IconHeadphones className="h-6 w-6 mb-2" />
                    <span>Тех. поддержка</span>
                  </Button>
                  <Button variant="outline" className="h-16 flex-col">
                    <IconMail className="h-6 w-6 mb-2" />
                    <span>Обратная связь</span>
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </SidebarInset>
    </>
  )
} 