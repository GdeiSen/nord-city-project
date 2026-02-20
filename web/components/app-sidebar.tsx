"use client"

import * as React from "react"
import {
  IconDashboard,
  IconUsers,
  IconTicket,
  IconCar,
  IconMessageCircle,
  IconBuildingSkyscraper,
  IconHistory,
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
  useSidebar,
} from "@/components/ui/sidebar"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

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
 * while secondary navigation includes supporting functions (help).
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
      title: "Гостевая парковка",
      url: "/guest-parking",
      icon: IconCar,
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
      title: "Журнал аудита",
      url: "/audit-log",
      icon: IconHistory,
    },
  ],
  
  navSecondary: [],
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
  const { state, isMobile } = useSidebar()

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
        {data.navSecondary.length > 0 && (
          <div className="mt-auto">
            <NavMain items={data.navSecondary} />
          </div>
        )}
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center justify-between gap-2 p-2 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:gap-1">
          <div className="flex-1 min-w-0 group-data-[collapsible=icon]:flex-none group-data-[collapsible=icon]:w-fit group-data-[collapsible=icon]:flex group-data-[collapsible=icon]:justify-center [&_[data-sidebar=menu]]:group-data-[collapsible=icon]:w-auto">
            <NavUser user={data.user} />
          </div>
          <div className="shrink-0 group-data-[collapsible=icon]:ml-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <ThemeToggle />
                </div>
              </TooltipTrigger>
              <TooltipContent
                side="right"
                align="center"
                sideOffset={8}
                hidden={state !== "collapsed" || isMobile}
              >
                Переключить тему
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
