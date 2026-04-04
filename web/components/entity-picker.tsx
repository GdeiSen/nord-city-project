"use client"

import * as React from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
} from "@tabler/icons-react"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 15

/** Simple option for filters and static lists */
export interface EntityPickerOption {
  value: string
  label: string
}

/** Config for generic data source */
export interface EntityPickerDataConfig<T = unknown> {
  /** Raw data items */
  data: T[]
  /** Extract value (id) from item */
  getValue: (item: T) => string | number
  /** Extract display label from item */
  getLabel: (item: T) => string
  /** Keys to search by when filtering (uses getLabel if not provided) */
  searchKeys?: (keyof T)[]
}

type EntityPickerBaseProps = {
  placeholder?: string
  emptyMessage?: string
  className?: string
  disabled?: boolean
}

/** Multi-select mode: value is comma-separated string */
export interface EntityPickerMultiProps extends EntityPickerBaseProps {
  multiple: true
  options?: EntityPickerOption[]
  dataConfig?: never
  value: string
  onChange: (value: string) => void
  onSelect?: never
}

/** Single-select mode with options */
export interface EntityPickerSingleOptionsProps extends EntityPickerBaseProps {
  multiple?: false
  options: EntityPickerOption[]
  dataConfig?: never
  value: string | number | null | undefined
  onSelect: (value: string) => void
  onChange?: never
}

/** Single-select mode with generic data */
export interface EntityPickerSingleDataProps<T = unknown> extends EntityPickerBaseProps {
  multiple?: false
  options?: never
  dataConfig: EntityPickerDataConfig<T>
  value: string | number | null | undefined
  onSelect: (item: T) => void
  onChange?: never
}

export type EntityPickerProps<T = unknown> =
  | EntityPickerMultiProps
  | EntityPickerSingleOptionsProps
  | EntityPickerSingleDataProps<T>

function buildSelectionSummary(labels: string[], placeholder: string): string {
  if (!labels.length) return placeholder
  if (labels.length === 1) return labels[0]
  return `${labels[0]} +${labels.length - 1}`
}

function clampDisplayLabel(label: string | null | undefined, maxLength = 72): string {
  const normalized = String(label || "").trim()
  if (!normalized) return ""
  if (normalized.length <= maxLength) return normalized
  return `${normalized.slice(0, maxLength - 1).trimEnd()}…`
}

function normalizeOptions<T>(
  props: EntityPickerProps<T>
): EntityPickerOption[] {
  if ("options" in props && props.options) {
    return props.options
  }
  if ("dataConfig" in props && props.dataConfig) {
    const { data, getValue, getLabel } = props.dataConfig
    return data.map((item) => ({
      value: String(getValue(item)),
      label: getLabel(item),
    }))
  }
  return []
}

function getRawItem<T>(props: EntityPickerProps<T>, value: string): T | null {
  if (!("dataConfig" in props) || !props.dataConfig) return null
  const { data, getValue } = props.dataConfig
  const item = data.find((d) => String(getValue(d)) === value)
  return item ?? null
}

export function EntityPicker<T = unknown>(props: EntityPickerProps<T>) {
  const {
    placeholder = "Выберите...",
    emptyMessage = "Нет вариантов",
    className,
    disabled = false,
  } = props

  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const [pageIndex, setPageIndex] = React.useState(0)
  const options = normalizeOptions(props)
  const isMulti = "multiple" in props && props.multiple === true
  const listId = React.useId()

  const filtered = React.useMemo(() => {
    if (!search.trim()) return options
    const q = search.toLowerCase()
    return options.filter(
      (o) =>
        o.label.toLowerCase().includes(q) || o.value.toLowerCase().includes(q)
    )
  }, [options, search])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pagedOptions = React.useMemo(() => {
    const start = pageIndex * PAGE_SIZE
    return filtered.slice(start, start + PAGE_SIZE)
  }, [filtered, pageIndex])

  React.useEffect(() => {
    setPageIndex(0)
  }, [search])

  React.useEffect(() => {
    if (!open) {
      setSearch("")
      setPageIndex(0)
    }
  }, [open])

  React.useEffect(() => {
    setPageIndex((current) => Math.min(current, pageCount - 1))
  }, [pageCount])

  if (isMulti) {
    const { value, onChange } = props
    const selectedIds = new Set(
      value ? String(value).split(",").map((s) => s.trim()).filter(Boolean) : []
    )
    const displayLabels = options
      .filter((o) => selectedIds.has(o.value))
      .map((o) => o.label)
    const triggerLabel = clampDisplayLabel(
      buildSelectionSummary(displayLabels, placeholder)
    ) || placeholder

    const toggle = (optValue: string) => {
      const next = new Set(selectedIds)
      if (next.has(optValue)) {
        next.delete(optValue)
      } else {
        next.add(optValue)
      }
      onChange(Array.from(next).join(","))
    }

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <div className="w-full min-w-0 max-w-full overflow-hidden">
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              role="combobox"
              disabled={disabled}
              className={cn(
                "grid h-10 w-full min-w-0 max-w-full shrink grid-cols-[minmax(0,1fr)_auto] items-center gap-2 overflow-hidden px-3 font-normal whitespace-normal",
                !displayLabels.length && "text-muted-foreground",
                className
              )}
              title={displayLabels.join(", ") || placeholder}
            >
              <span className="block min-w-0 max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-left">
                {triggerLabel}
              </span>
              <IconChevronDown className="h-4 w-4 shrink-0 opacity-50" />
            </Button>
          </PopoverTrigger>
        </div>
        <PopoverContent
          className="flex max-h-[min(420px,var(--radix-popper-available-height))] w-[min(var(--radix-popover-trigger-width),calc(100vw-2rem))] max-w-[calc(100vw-2rem)] min-w-0 flex-col overflow-hidden p-0"
          align="start"
        >
          <div className="shrink-0 border-b p-2">
            <Input
              placeholder="Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8"
              autoFocus
              onKeyDown={(e) => e.stopPropagation()}
            />
          </div>
          <ScrollArea className="min-h-0 flex-1">
            <div className="overflow-x-auto">
              <div id={listId} className="min-w-full w-max p-1">
                {filtered.length === 0 ? (
                  <div className="py-4 text-center text-sm text-muted-foreground">
                    {emptyMessage}
                  </div>
                ) : (
                  pagedOptions.map((opt) => (
                    <label
                      key={opt.value}
                      className="flex min-w-0 max-w-full cursor-pointer items-center gap-2 overflow-hidden rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                    >
                      <Checkbox
                        checked={selectedIds.has(opt.value)}
                        onCheckedChange={() => toggle(opt.value)}
                      />
                      <span
                        className="block min-w-0 max-w-full flex-1 overflow-hidden text-ellipsis whitespace-nowrap pr-2"
                        title={opt.label}
                      >
                        {opt.label}
                      </span>
                    </label>
                  ))
                )}
              </div>
            </div>
          </ScrollArea>
          <div className="z-10 flex shrink-0 items-center justify-between gap-2 border-t bg-popover p-2">
            <div className="text-xs text-muted-foreground">
              {filtered.length > 0 ? `${pageIndex + 1}/${pageCount}` : "0/0"}
            </div>
            <div className="ml-auto flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setPageIndex((current) => Math.max(0, current - 1))}
                disabled={pageIndex === 0 || filtered.length === 0}
              >
                <IconChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() =>
                  setPageIndex((current) => Math.min(pageCount - 1, current + 1))
                }
                disabled={pageIndex >= pageCount - 1 || filtered.length === 0}
              >
                <IconChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  // Single select
  const valueStr = props.value != null ? String(props.value) : ""
  const selectedOption = options.find((o) => o.value === valueStr)
  const displayLabel = selectedOption?.label ?? null
  const triggerLabel = clampDisplayLabel(displayLabel) || placeholder

  const handleSelect = (optValue: string) => {
    if ("dataConfig" in props && props.dataConfig) {
      const item = getRawItem(props, optValue)
      if (item) props.onSelect(item)
    } else {
      (props as EntityPickerSingleOptionsProps).onSelect(optValue)
    }
    setOpen(false)
    setSearch("")
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className="w-full min-w-0 max-w-full overflow-hidden">
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            disabled={disabled}
            className={cn(
              "grid h-10 w-full min-w-0 max-w-full shrink grid-cols-[minmax(0,1fr)_auto] items-center gap-2 overflow-hidden px-3 font-normal whitespace-normal",
              !displayLabel && "text-muted-foreground",
              className
            )}
            title={displayLabel ?? placeholder}
          >
            <span className="block min-w-0 max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-left">
              {triggerLabel}
            </span>
            <IconChevronDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
      </div>
      <PopoverContent
        className="flex max-h-[min(420px,var(--radix-popper-available-height))] w-[min(var(--radix-popover-trigger-width),calc(100vw-2rem))] max-w-[calc(100vw-2rem)] min-w-0 flex-col overflow-hidden p-0"
        align="start"
      >
        <div className="shrink-0 border-b p-2">
          <Input
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
            autoFocus
            onKeyDown={(e) => e.stopPropagation()}
          />
        </div>
        <ScrollArea className="min-h-0 flex-1">
          <div className="overflow-x-auto">
            <div id={listId} className="min-w-full w-max p-1">
              {filtered.length === 0 ? (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  {emptyMessage}
                </div>
              ) : (
                pagedOptions.map((opt) => (
                  <label
                    key={opt.value}
                    className="flex min-w-0 max-w-full cursor-pointer items-center gap-2 overflow-hidden rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                    onClick={() => handleSelect(opt.value)}
                  >
                    <Checkbox
                      checked={valueStr === opt.value}
                      onCheckedChange={() => handleSelect(opt.value)}
                    />
                    <span
                      className="block min-w-0 max-w-full flex-1 overflow-hidden text-ellipsis whitespace-nowrap pr-2"
                      title={opt.label}
                    >
                      {opt.label}
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>
        </ScrollArea>
        <div className="z-10 flex shrink-0 items-center justify-between gap-2 border-t bg-popover p-2">
          <div className="text-xs text-muted-foreground">
            {filtered.length > 0 ? `${pageIndex + 1}/${pageCount}` : "0/0"}
          </div>
          <div className="ml-auto flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPageIndex((current) => Math.max(0, current - 1))}
              disabled={pageIndex === 0 || filtered.length === 0}
            >
              <IconChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() =>
                setPageIndex((current) => Math.min(pageCount - 1, current + 1))
              }
              disabled={pageIndex >= pageCount - 1 || filtered.length === 0}
            >
              <IconChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
