"use client"

import * as React from "react"
import { IconFile, IconTrash } from "@tabler/icons-react"
import { toast } from "sonner"

import { storageApi } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"

type StorageUploadKind = "image" | "video" | "document"

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"]
const VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"]
const DOCUMENT_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
]
const DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".csv"]
const ACCEPT_MAP: Record<StorageUploadKind, string[]> = {
  image: IMAGE_TYPES,
  video: VIDEO_TYPES,
  document: [...DOCUMENT_TYPES, ...DOCUMENT_EXTENSIONS],
}
const MAX_SIZE_BY_KIND: Record<StorageUploadKind, number> = {
  image: 5 * 1024 * 1024,
  video: 20 * 1024 * 1024,
  document: 20 * 1024 * 1024,
}

export interface StorageUploaderProps {
  value?: string[]
  onChange: (urls: string[]) => void
  label?: string
  description?: string
  className?: string
  category?: string
  maxItems?: number
  acceptedKinds?: StorageUploadKind[]
}

function getFileExtension(name: string): string {
  const parts = String(name || "").toLowerCase().split(".")
  return parts.length > 1 ? `.${parts.pop()}` : ""
}

function isImageUrl(url: string): boolean {
  return /\.(jpe?g|png|gif|webp|svg)(\?|$)/i.test(url)
}

function getDisplayName(url: string): string {
  const tail = url.split("/").pop() || "file"
  const cleaned = tail.split("?")[0]
  const normalized = cleaned.replace(/^(?:[a-f0-9]{32}_)+/i, "")
  return normalized || cleaned
}

export function StorageUploader({
  value,
  onChange,
  label,
  description,
  className,
  category = "DEFAULT",
  maxItems = 10,
  acceptedKinds = ["image", "document"],
}: StorageUploaderProps) {
  const urls = value ?? []
  const [uploading, setUploading] = React.useState(false)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const acceptedTokens = React.useMemo(
    () => acceptedKinds.flatMap((kind) => ACCEPT_MAP[kind]),
    [acceptedKinds]
  )

  const validateFile = React.useCallback(
    (file: File): string | null => {
      const extension = getFileExtension(file.name)
      const matches = acceptedKinds.some((kind) => {
        if (kind === "document") {
          return DOCUMENT_TYPES.includes(file.type) || DOCUMENT_EXTENSIONS.includes(extension)
        }
        return ACCEPT_MAP[kind].includes(file.type)
      })

      if (!matches) {
        return "Неподдерживаемый формат файла"
      }

      const matchedKind =
        acceptedKinds.find((kind) => {
          if (kind === "document") {
            return DOCUMENT_TYPES.includes(file.type) || DOCUMENT_EXTENSIONS.includes(extension)
          }
          return ACCEPT_MAP[kind].includes(file.type)
        }) || acceptedKinds[0]

      const maxSize = MAX_SIZE_BY_KIND[matchedKind]
      if (file.size > maxSize) {
        return `Файл слишком большой: ${(file.size / 1024 / 1024).toFixed(1)} МБ`
      }

      return null
    },
    [acceptedKinds]
  )

  const handleFiles = React.useCallback(
    async (files: FileList | null) => {
      if (!files?.length || uploading) return
      if (urls.length >= maxItems) {
        toast.error(`Максимум ${maxItems} файлов`)
        return
      }

      setUploading(true)
      const nextUrls = [...urls]

      try {
        for (const file of Array.from(files)) {
          if (nextUrls.length >= maxItems) break
          const error = validateFile(file)
          if (error) {
            toast.error(error, { description: file.name })
            continue
          }

          const result = await storageApi.upload(file, { category })
          nextUrls.push(result.url)
          onChange([...nextUrls])
        }
      } catch (error: any) {
        toast.error("Ошибка загрузки", {
          description: error?.message ?? "Попробуйте еще раз.",
        })
      } finally {
        setUploading(false)
      }
    },
    [category, maxItems, onChange, uploading, urls, validateFile]
  )

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleFiles(event.target.files)
    event.target.value = ""
  }

  return (
    <div className={cn("w-full min-w-0 max-w-full space-y-3", className)}>
      {label && <Label className="font-medium">{label}</Label>}
      {description && <p className="text-sm text-muted-foreground">{description}</p>}

      <div className="w-full min-w-0 rounded-md border border-input bg-transparent p-4">
        <input
          ref={inputRef}
          type="file"
          accept={acceptedTokens.join(",")}
          multiple
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="flex min-w-0 max-w-full flex-col gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => inputRef.current?.click()}
            disabled={uploading || urls.length >= maxItems}
            className="max-w-full justify-start"
          >
            {uploading ? <Spinner className="size-4" /> : <IconFile className="h-4 w-4" />}
            {uploading ? "Загрузка..." : "Выбрать файлы"}
          </Button>

          <p className="text-xs text-muted-foreground">
            До {maxItems} файлов. Изображения до 5 МБ, документы и видео до 20 МБ.
          </p>

          {urls.length > 0 && (
            <div className="min-w-0 max-w-full space-y-2">
              {urls.map((url, index) => (
                <div
                  key={`${url}-${index}`}
                  className="flex min-w-0 max-w-full items-center gap-3 overflow-hidden rounded-md border bg-muted/20 px-3 py-2"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded bg-muted">
                    {isImageUrl(url) ? (
                      <img src={url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <IconFile className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                  <div className="min-w-0 max-w-full flex-1 overflow-hidden">
                    <p className="truncate text-sm font-medium">{getDisplayName(url)}</p>
                    <p
                      className="block max-w-full truncate text-xs text-muted-foreground"
                      title={url}
                    >
                      {url}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => onChange(urls.filter((_, itemIndex) => itemIndex !== index))}
                  >
                    <IconTrash className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
