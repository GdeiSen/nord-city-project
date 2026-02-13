"use client"

import { useState, useEffect, useRef } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription } from "@/components/ui/drawer"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { IconSearch, IconExternalLink } from "@tabler/icons-react"
import { useIsMobile } from "@/hooks/use-mobile"

export interface DataPickerField {
  /** Field key for data access */
  key: string
  /** Display label for the field */
  label: string
  /** Whether this field should be searchable */
  searchable?: boolean
  /** Custom render function for the field */
  render?: (value: any, item: any) => React.ReactNode
}

export interface DataPickerProps<T = any> {
  /** Title of the picker */
  title: string
  /** Description of the picker */
  description: string
  /** Data array to display */
  data: T[]
  /** Fields configuration for display */
  fields: DataPickerField[]
  /** Current selected value */
  value?: any
  /** Display value for the input (what user sees) */
  displayValue?: string
  /** Placeholder for the input */
  placeholder?: string
  /** Callback when item is selected */
  onSelect: (item: T) => void
  /** Whether picker is open */
  open: boolean
  /** Callback when open state changes */
  onOpenChange: (open: boolean) => void
  /** Custom search function */
  customSearch?: (item: T, searchTerm: string) => boolean
}

export function DataPicker<T = any>({
  title,
  description,
  data,
  fields,
  value,
  displayValue,
  placeholder = "Не выбрано",
  onSelect,
  open,
  onOpenChange,
  customSearch
}: DataPickerProps<T>) {
  const isMobile = useIsMobile()
  const [searchTerm, setSearchTerm] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Ensure input stays focused when drawer/sheet opens
  useEffect(() => {
    if (open && inputRef.current) {
      // Small delay to ensure drawer/sheet is fully rendered
      const timer = setTimeout(() => {
        inputRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [open])

  const searchableFields = fields.filter(f => f.searchable !== false)
  
  const filteredData = data.filter(item => {
    if (!searchTerm) return true
    if (customSearch) return customSearch(item, searchTerm)
    
    const lowerSearch = searchTerm.toLowerCase()
    return searchableFields.some(field => {
      const fieldValue = (item as any)[field.key]
      if (typeof fieldValue === 'string') {
        return fieldValue.toLowerCase().includes(lowerSearch)
      }
      if (typeof fieldValue === 'number') {
        return fieldValue.toString().includes(lowerSearch)
      }
      return false
    })
  })

  const handleSelect = (item: T) => {
    onSelect(item)
    onOpenChange(false)
    setSearchTerm('')
  }

  // Prevent focus from being stolen by drawer/sheet
  const handleKeyDown = (e: React.KeyboardEvent) => {
    e.stopPropagation()
  }

  const handleInputFocus = (e: React.FocusEvent) => {
    e.stopPropagation()
  }

  const Content = () => (
    <>
      <div 
        className="p-4 space-y-3"
        onKeyDown={handleKeyDown}
        onFocus={handleInputFocus}
      >
        <div className="relative">
          <IconSearch className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            ref={inputRef}
            placeholder="Поиск..." 
            className="pl-8" 
            value={searchTerm} 
            onChange={e => setSearchTerm(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={handleInputFocus}
            autoFocus
          />
        </div>
        <div className="rounded-md border max-h-[60vh] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {fields.map(field => (
                  <TableHead key={field.key}>{field.label}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredData.map((item, index) => (
                <TableRow 
                  key={index} 
                  className="cursor-pointer hover:bg-accent" 
                  onClick={() => handleSelect(item)}
                >
                  {fields.map(field => (
                    <TableCell key={field.key}>
                      {field.render 
                        ? field.render((item as any)[field.key], item)
                        : (item as any)[field.key]
                      }
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </>
  )

  return (
    <>
      {/* Display selected text and a button to open picker */}
      <div className="flex items-center gap-2">
        <div className="flex-1 px-3 py-2 rounded-md border bg-background text-sm truncate">
          {displayValue && displayValue.trim().length > 0 ? (
            displayValue
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </div>
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Открыть выбор данных"
          onClick={() => onOpenChange(true)}
        >
          <IconExternalLink className="h-4 w-4" />
        </Button>
      </div>

      {/* Picker modal */}
      {isMobile ? (
        <Drawer open={open} onOpenChange={onOpenChange}>
          <DrawerContent className="p-0">
            <DrawerHeader>
              <DrawerTitle>{title}</DrawerTitle>
              <DrawerDescription>{description}</DrawerDescription>
            </DrawerHeader>
            <div className="overflow-y-auto max-h-[calc(100dvh-4.5rem)] pb-[50dvh]">
              <Content />
            </div>
          </DrawerContent>
        </Drawer>
      ) : (
        <Sheet open={open} onOpenChange={onOpenChange}>
          <SheetContent side="right" className="sm:max-w-md">
            <SheetHeader>
              <SheetTitle>{title}</SheetTitle>
              <SheetDescription>{description}</SheetDescription>
            </SheetHeader>
            <Content />
          </SheetContent>
        </Sheet>
      )}
    </>
  )
}
