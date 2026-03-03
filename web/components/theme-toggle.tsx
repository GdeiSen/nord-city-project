"use client"

import * as React from "react"
import { useTheme } from "next-themes"
import { IconSun, IconMoon, IconDeviceLaptop } from "@tabler/icons-react"

import { useMarqueeAnimationsDisabled } from "@/hooks/ui/use-marquee-animations"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Switch } from "@/components/ui/switch"

/**
 * Theme toggle component for switching between light, dark, and system themes
 * 
 * This component provides a dropdown menu that allows users to switch between
 * different theme modes. It uses next-themes for theme management and displays
 * appropriate icons for each theme state. The component includes system theme
 * detection for automatic theme switching based on user's OS preferences.
 * 
 * Features:
 * - Light theme toggle
 * - Dark theme toggle  
 * - System theme detection
 * - Smooth transitions
 * - Accessible keyboard navigation
 * 
 * @returns {JSX.Element} Theme toggle dropdown button
 */
export function ThemeToggle() {
  const { setTheme, theme } = useTheme()
  const [animationsDisabled, setAnimationsDisabled] = useMarqueeAnimationsDisabled()
  const [mounted, setMounted] = React.useState(false)

  // Avoid hydration mismatch
  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className="h-8 w-8">
        <IconSun className="h-4 w-4" />
        <span className="sr-only">Переключить тему</span>
      </Button>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          {theme === "light" && <IconSun className="h-4 w-4" />}
          {theme === "dark" && <IconMoon className="h-4 w-4" />}
          {theme === "system" && <IconDeviceLaptop className="h-4 w-4" />}
          <span className="sr-only">Переключить тему</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem 
          onClick={() => setTheme("light")}
          className="cursor-pointer"
        >
          <IconSun className="mr-2 h-4 w-4" />
          <span>Светлая</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setTheme("dark")}
          className="cursor-pointer"
        >
          <IconMoon className="mr-2 h-4 w-4" />
          <span>Темная</span>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => setTheme("system")}
          className="cursor-pointer"
        >
          <IconDeviceLaptop className="mr-2 h-4 w-4" />
          <span>Системная</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={(event) => event.preventDefault()}
          onClick={() => setAnimationsDisabled(!animationsDisabled)}
          className="cursor-pointer justify-between gap-3"
        >
          <div className="space-y-0.5">
            <div className="text-sm">Отключить анимации</div>
            <div className="text-xs text-muted-foreground">
              Бегущие строки в таблицах
            </div>
          </div>
          <Switch
            checked={animationsDisabled}
            onCheckedChange={setAnimationsDisabled}
            onClick={(event) => event.stopPropagation()}
            aria-label="Отключить анимации"
          />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
} 
