"use client"

import * as React from "react"
import {
  IconDashboard,
  IconUsers,
  IconTicket,
  IconMessageCircle,
  IconBuildingSkyscraper,
  IconChartBar,
  IconSettings,
  IconHelp,
  IconBell,
  IconReportAnalytics,
} from "@tabler/icons-react"

import { NavMain } from "@/components/nav-main"
import { NavUser } from "@/components/nav-user"
import { ThemeToggle } from "@/components/theme-toggle"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

/**
 * Navigation data configuration for the Business Center Management System
 * 
 * This data structure defines the complete navigation hierarchy for the
 * administrative interface. It includes user context information and
 * segregates navigation items into primary and secondary categories
 * for better information architecture and user experience.
 * 
 * The navigation structure follows a logical grouping where primary
 * navigation contains core business operations (users, tickets, spaces)
 * while secondary navigation includes system functions (settings, reports).
 * 
 * @type {Object} Navigation configuration object
 */
const data = {
  /**
   * Current user information for profile display
   * 
   * In production, this would be dynamically populated from the
   * authentication context or user session data.
   */
  user: {
    name: "Администратор",
    email: "admin@businesscenter.ru",
    avatar: "/avatars/admin-avatar.jpg",
  },
  
  /**
   * Primary navigation items for core business operations
   * 
   * These represent the main functional areas of the business center
   * management system, ordered by usage frequency and importance.
   */
  navMain: [
    {
      title: "Панель управления",
      url: "/",
      icon: IconDashboard,
    },
    {
      title: "Пользователи",
      url: "/users",
      icon: IconUsers,
    },
    {
      title: "Заявки на обслуживание",
      url: "/service-tickets", 
      icon: IconTicket,
    },
    {
      title: "Отзывы",
      url: "/feedbacks",
      icon: IconMessageCircle,
    },
    {
      title: "Бизнес-центры",
      url: "/spaces",
      icon: IconBuildingSkyscraper,
    },
    {
      title: "Аналитика",
      url: "/analytics",
      icon: IconChartBar,
    },
  ],
  
  /**
   * Secondary navigation items for system administration
   * 
   * These represent supporting functions and administrative tools
   * that are used less frequently but are essential for system
   * maintenance and reporting.
   */
  navSecondary: [
    {
      title: "Уведомления",
      url: "/notifications",
      icon: IconBell,
    },
    {
      title: "Отчеты",
      url: "/reports",
      icon: IconReportAnalytics,
    },
    {
      title: "Настройки",
      url: "/settings",
      icon: IconSettings,
    },
    {
      title: "Помощь",
      url: "/help",
      icon: IconHelp,
    },
  ],
}

/**
 * Application sidebar component for the Business Center Management System
 * 
 * This component provides the primary navigation interface for administrators,
 * featuring a collapsible design that adapts to different screen sizes and
 * user preferences. The sidebar includes hierarchical navigation with visual
 * icons, user profile information, responsive behavior, and theme switching.
 * 
 * Key features:
 * - Collapsible design with icon-only mode for space efficiency
 * - Hierarchical navigation structure with primary and secondary sections
 * - Integrated user profile display with authentication context
 * - Theme switching functionality (light/dark/system)
 * - Responsive design that adapts to mobile and desktop viewports
 * - Accessibility support with proper ARIA attributes and keyboard navigation
 * 
 * The component uses the shadcn/ui Sidebar components for consistent styling
 * and behavior across the application while maintaining customization flexibility.
 * 
 * @param {React.ComponentProps<typeof Sidebar>} props - Standard sidebar component props
 * @returns {JSX.Element} The complete sidebar navigation interface with theme toggle
 */
export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <a href="/">
                <IconBuildingSkyscraper className="!size-6" />
                <span className="text-base font-semibold">Управление БЦ</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <div className="mt-auto">
          <NavMain items={data.navSecondary} />
        </div>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center justify-between p-2">
          <div className="flex-1">
            <NavUser user={data.user} />
          </div>
          <div className="ml-2">
            <ThemeToggle />
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
