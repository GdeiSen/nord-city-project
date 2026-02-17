"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { IconFilter } from "@tabler/icons-react"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"

export interface DataTableToolbarProps {
  globalQuery: string
  onGlobalQueryChange: (value: string) => void
  isSortFilterOpen: boolean
  onSortFilterOpenChange: (open: boolean) => void
  activeSortsCount: number
  activeFiltersCount: number
  sortFilterContent: React.ReactNode
  isMobile: boolean
}

export function DataTableToolbar({
  globalQuery,
  onGlobalQueryChange,
  isSortFilterOpen,
  onSortFilterOpenChange,
  activeSortsCount,
  activeFiltersCount,
  sortFilterContent,
  isMobile,
}: DataTableToolbarProps) {
  const triggerButton = (
    <Button variant="outline" size="sm" className="h-9">
      <IconFilter className="h-4 w-4" />
      {(activeSortsCount > 0 || activeFiltersCount > 0) && (
        <Badge variant="secondary" className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center">
          {activeSortsCount + activeFiltersCount}
        </Badge>
      )}
    </Button>
  )

  return (
    <div className="flex w-full items-center gap-2">
      <Input
        placeholder="Поиск по таблице..."
        value={globalQuery}
        onChange={(e) => onGlobalQueryChange(e.target.value)}
        className="h-9"
      />
      {isMobile ? (
        <Drawer open={isSortFilterOpen} onOpenChange={onSortFilterOpenChange}>
          <DrawerTrigger asChild>{triggerButton}</DrawerTrigger>
          <DrawerContent className="p-0 flex flex-col max-h-[90dvh]">
            <DrawerHeader className="shrink-0">
              <DrawerTitle>Сортировка и фильтры</DrawerTitle>
              <DrawerDescription>Настройте сортировку и фильтры для таблицы</DrawerDescription>
            </DrawerHeader>
            <ScrollArea className="flex-1 min-h-0 px-4">
              <div className="pb-4">{sortFilterContent}</div>
            </ScrollArea>
            <DrawerFooter className="shrink-0">
              <DrawerClose asChild>
                <Button variant="outline">Закрыть</Button>
              </DrawerClose>
            </DrawerFooter>
          </DrawerContent>
        </Drawer>
      ) : (
        <Sheet open={isSortFilterOpen} onOpenChange={onSortFilterOpenChange}>
          <SheetTrigger asChild>{triggerButton}</SheetTrigger>
          <SheetContent side="right" className="flex flex-col w-full sm:max-w-md p-0">
            <SheetHeader className="p-4 pb-2 shrink-0">
              <SheetTitle>Сортировка и фильтры</SheetTitle>
              <SheetDescription>Настройте сортировку и фильтры для таблицы</SheetDescription>
            </SheetHeader>
            <ScrollArea className="flex-1 px-4 min-h-0">
              <div className="pb-4">{sortFilterContent}</div>
            </ScrollArea>
          </SheetContent>
        </Sheet>
      )}
    </div>
  )
}
