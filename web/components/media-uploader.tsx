"use client"

import * as React from "react"
import { IconChevronLeft, IconChevronRight, IconPhoto, IconTrash, IconVideo } from "@tabler/icons-react"
import { toast } from "sonner"

import { cn } from "@/lib/utils"
import { mediaApi } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"

// Limits
const MAX_ITEMS = 10
const MAX_IMAGE_SIZE = 5 * 1024 * 1024   // 5 MB
const MAX_VIDEO_SIZE = 20 * 1024 * 1024  // 20 MB
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
const VIDEO_TYPES = ["video/mp4", "video/webm"]

export interface MediaUploaderProps {
  value?: string[]
  onChange: (urls: string[]) => void
  label?: string
  description?: string
  className?: string
}

export function MediaUploader({
  value,
  onChange,
  label,
  description,
  className,
}: MediaUploaderProps) {
  const urls = value ?? []
  const [isDragging, setIsDragging] = React.useState(false)
  const [uploadingIndex, setUploadingIndex] = React.useState<number | null>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const isImage = (url: string) =>
    /\.(jpe?g|png|gif|webp)(\?|$)/i.test(url) ||
    /image\/(jpeg|png|gif|webp)/.test(url)

  const validateFile = (file: File): string | null => {
    if (!file || typeof file.type !== "string") {
      return "Некорректный файл"
    }
    const isImg = IMAGE_TYPES.includes(file.type)
    const isVid = VIDEO_TYPES.includes(file.type)
    if (!isImg && !isVid) {
      return `Неподдерживаемый формат. Фото: JPEG, PNG, GIF, WebP. Видео: MP4, WebM`
    }
    if (isImg && file.size > MAX_IMAGE_SIZE) {
      return `Фото до 5 МБ. Файл: ${(file.size / 1024 / 1024).toFixed(1)} МБ`
    }
    if (isVid && file.size > MAX_VIDEO_SIZE) {
      return `Видео до 20 МБ. Файл: ${(file.size / 1024 / 1024).toFixed(1)} МБ`
    }
    return null
  }

  const handleFiles = React.useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return
      if (urls.length >= MAX_ITEMS) {
        toast.error(`Максимум ${MAX_ITEMS} файлов`)
        return
      }

      const fileArray = Array.from(files)
      const toAdd = Math.min(fileArray.length, MAX_ITEMS - urls.length)
      const nextUrls = [...urls]

      for (let i = 0; i < toAdd; i++) {
        const file = fileArray[i]
        if (!file) continue
        const err = validateFile(file)
        if (err) {
          toast.error(err)
          continue
        }

        setUploadingIndex(nextUrls.length)
        try {
          const result = await mediaApi.upload(file)
          nextUrls.push(result.url)
          onChange(nextUrls)
        } catch (e: any) {
          toast.error(e?.message ?? "Ошибка загрузки")
        } finally {
          setUploadingIndex(null)
        }
      }
    },
    [urls, onChange]
  )

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files)
    e.target.value = ""
  }

  const handleRemove = (index: number) => {
    onChange(urls.filter((_, i) => i !== index))
  }

  const handleMove = (index: number, direction: "left" | "right") => {
    const newIndex = direction === "left" ? index - 1 : index + 1
    if (newIndex < 0 || newIndex >= urls.length) return
    const next = [...urls]
    ;[next[index], next[newIndex]] = [next[newIndex], next[index]]
    onChange(next)
  }

  const canAdd = urls.length < MAX_ITEMS

  return (
    <div className={cn("space-y-3", className)}>
      {label && <Label className="font-medium">{label}</Label>}
      {description && (
        <p className="text-sm text-muted-foreground">{description}</p>
      )}

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          "rounded-md border border-input bg-transparent p-6 text-center shadow-xs transition-colors",
          isDragging && canAdd && "border-ring bg-primary/5"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={[...IMAGE_TYPES, ...VIDEO_TYPES].join(",")}
          multiple
          onChange={handleInputChange}
          className="hidden"
        />
        {uploadingIndex !== null ? (
          <div className="flex flex-col items-center gap-2 text-muted-foreground">
            <Spinner className="size-8" />
            <span className="text-sm">Загрузка...</span>
          </div>
        ) : canAdd ? (
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            className="cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            <Empty className="border-0 p-0">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconPhoto className="size-6" />
                </EmptyMedia>
                <EmptyTitle className="text-sm font-medium">
                  Перетащите сюда или нажмите для выбора
                </EmptyTitle>
                <EmptyDescription>
                  Фото до 5 МБ · Видео до 20 МБ · Не более {MAX_ITEMS} файлов
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            Достигнут лимит ({MAX_ITEMS} файлов)
          </p>
        )}
      </div>

      {urls.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {urls.map((url, index) => (
            <div
              key={`${index}-${url}`}
              className="group relative aspect-video overflow-hidden rounded-md border bg-muted"
            >
              {isImage(url) ? (
                <img
                  src={url}
                  alt=""
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-muted">
                  <IconVideo className="size-8 text-muted-foreground" />
                </div>
              )}
              <div className="absolute inset-x-1 top-1 flex justify-between opacity-0 transition-opacity group-hover:opacity-100">
                <div className="flex gap-0.5">
                  <Button
                    type="button"
                    variant="secondary"
                    size="icon-sm"
                    className="h-7 w-7 bg-muted/90 hover:bg-muted"
                    onClick={() => handleMove(index, "left")}
                    disabled={index === 0}
                    aria-label="Переместить влево"
                  >
                    <IconChevronLeft className="size-3.5" />
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="icon-sm"
                    className="h-7 w-7 bg-muted/90 hover:bg-muted"
                    onClick={() => handleMove(index, "right")}
                    disabled={index === urls.length - 1}
                    aria-label="Переместить вправо"
                  >
                    <IconChevronRight className="size-3.5" />
                  </Button>
                </div>
                <Button
                  type="button"
                  variant="secondary"
                  size="icon-sm"
                  className="h-7 w-7 bg-muted/90 hover:bg-muted"
                  onClick={() => handleRemove(index)}
                  aria-label="Удалить"
                >
                  <IconTrash className="size-3.5" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
