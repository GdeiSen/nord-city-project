"use client"

import * as React from "react"
import { IconPlus, IconTrash } from "@tabler/icons-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

interface PhotoLinksEditorProps {
  value?: string[]
  onChange: (links: string[]) => void
  label?: string
  description?: string
  addButtonLabel?: string
  emptyStateText?: string
  className?: string
  inputPlaceholder?: string
}

export function PhotoLinksEditor({
  value,
  onChange,
  label,
  description,
  addButtonLabel = "Добавить ссылку",
  emptyStateText = "Ссылки не добавлены",
  className,
  inputPlaceholder = "https://example.com/photo.jpg",
}: PhotoLinksEditorProps) {
  const links = value ?? []

  const handleChange = React.useCallback(
    (index: number, nextValue: string) => {
      const nextLinks = [...links]
      nextLinks[index] = nextValue
      onChange(nextLinks)
    },
    [links, onChange]
  )

  const handleAdd = React.useCallback(() => {
    onChange([...links, ""])
  }, [links, onChange])

  const handleRemove = React.useCallback(
    (index: number) => {
      onChange(links.filter((_, i) => i !== index))
    },
    [links, onChange]
  )

  return (
    <div className={cn("space-y-3", className)}>
      {label && <Label className="font-medium">{label}</Label>}
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}

      <div className="space-y-2">
        {links.map((link, index) => (
          <div key={`${index}-${link}`} className="flex items-center gap-2">
            <Input
              value={link}
              onChange={(event) => handleChange(index, event.target.value)}
              placeholder={inputPlaceholder}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => handleRemove(index)}
              aria-label="Удалить ссылку"
            >
              <IconTrash className="h-4 w-4" />
            </Button>
          </div>
        ))}

        {links.length === 0 && (
          <div className="text-sm text-muted-foreground border border-dashed rounded-md p-3 bg-muted/30">
            {emptyStateText}
          </div>
        )}

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleAdd}
        >
          <IconPlus className="h-4 w-4" />
          {addButtonLabel}
        </Button>
      </div>
    </div>
  )
}

