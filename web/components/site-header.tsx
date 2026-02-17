"use client"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { usePathname } from "next/navigation"

/**
 * Site header component for the Business Center Management System
 * 
 * This component provides the primary navigation header that adapts dynamically
 * to the current page context. It displays contextual page titles, breadcrumb
 * navigation for nested routes, and provides access to external resources and
 * documentation. The component integrates with Next.js routing to automatically
 * update its content based on the active route.
 * 
 * Key features:
 * - Dynamic page title generation based on current route
 * - Contextual breadcrumb navigation for hierarchical pages
 * - Responsive design with mobile-optimized controls
 * - Integration with sidebar toggle functionality
 * - Quick access to documentation and source code
 * 
 * The header maintains consistent branding and navigation patterns across
 * all pages while providing route-specific context to improve user orientation.
 * 
 * @returns {JSX.Element} Responsive header component with dynamic content
 */
export function SiteHeader() {
  const pathname = usePathname()

  /**
   * Generates localized page title based on current route
   * 
   * This function maps URL pathnames to human-readable Russian titles for
   * display in the header. It supports both static routes and dynamic routes
   * with parameter-based matching for nested navigation structures.
   * 
   * The function uses a switch statement for performance optimization and
   * provides fallback logic for undefined routes to maintain a consistent
   * user experience even when navigating to unmapped pages.
   * 
   * @returns {string} Localized page title corresponding to current route
   */
  const getPageTitle = () => {
    switch (pathname) {
      case '/':
        return 'Панель управления'
      case '/users':
        return 'Пользователи'
      case '/service-tickets':
        return 'Заявки на обслуживание'
      case '/feedbacks':
        return 'Отзывы пользователей'
      case '/spaces':
        return 'Бизнес-центры'
      default:
        if (pathname.startsWith('/spaces/')) {
          return 'Помещения бизнес-центра'
        }
        return 'Управление БЦ'
    }
  }

  /**
   * Generates breadcrumb navigation for hierarchical routes
   * 
   * This function analyzes the current pathname to determine if breadcrumb
   * navigation should be displayed and constructs appropriate breadcrumb
   * elements for nested routes. It provides contextual navigation aids for
   * users navigating through hierarchical page structures.
   * 
   * The function currently supports spaces detail pages but can be extended
   * to handle additional nested routes as the application grows. It returns
   * null for routes that don't require breadcrumb navigation to maintain
   * clean header design.
   * 
   * @returns {JSX.Element | null} Breadcrumb navigation component or null
   */
  const getBreadcrumbs = () => {
    const segments = pathname.split('/').filter(Boolean)
    
    if (segments.length === 0) {
      return null
    }

    if (segments.length === 1) {
      return null
    }

    // Handle nested routes like /spaces/[id]
    if (segments[0] === 'spaces' && segments[1]) {
      return (
        <div className="flex items-center text-sm text-muted-foreground">
          <a href="/spaces" className="hover:text-foreground">
            Бизнес-центры
          </a>
          <span className="mx-2">/</span>
          <span>Помещения</span>
        </div>
      )
    }

    return null
  }

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 h-4"
        />
        <div className="flex flex-col">
          <h1 className="text-base font-medium">{getPageTitle()}</h1>
          {getBreadcrumbs()}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" asChild size="sm" className="hidden sm:flex">
            <a
              href="https://evergreen-explorers.notion.site/2a2b3c9f18788038a599c94f907020c0"
              rel="noopener noreferrer"
              target="_blank"
              className="text-foreground"
            >
              Руководство пользователя
            </a>
          </Button>
        </div>
      </div>
    </header>
  )
}
