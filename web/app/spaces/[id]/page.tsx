"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import {
  IconChevronLeft,
  IconEdit,
  IconLink,
  IconPlus,
  IconTrash,
} from "@tabler/icons-react"
import { ColumnDef } from "@tanstack/react-table"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { PhotoLinksEditor } from "@/components/photo-links-editor"
import { PageHeader } from "@/components/page-header"
import { DataTable } from "@/components/data-table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { SidebarInset } from "@/components/ui/sidebar"
import { SiteHeader } from "@/components/site-header"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { useIsMobile } from "@/hooks/use-mobile"
import { useLoading } from "@/hooks/use-loading"
import { rentalObjectApi, rentalSpaceApi } from "@/lib/api"
import { RentalObject, RentalSpace } from "@/types"

type SpaceStatusVariant = "default" | "secondary" | "destructive" | "outline"

const SPACE_STATUS_LABELS: Record<string, string> = {
  FREE: "Свободно",
  RESERVED: "Забронировано",
  OCCUPIED: "Сдано",
  MAINTENANCE: "На обслуживании",
}

const SPACE_STATUS_VARIANTS: Record<string, SpaceStatusVariant> = {
  FREE: "default",
  RESERVED: "secondary",
  OCCUPIED: "destructive",
  MAINTENANCE: "outline",
}

const DEFAULT_SPACE_STATUS = "FREE"

export default function RentalObjectSpacesPage() {
  const params = useParams<{ id: string }>()
  const router = useRouter()
  const isMobile = useIsMobile()
  const { loading, withLoading } = useLoading(true)

  const objectId = Number(params?.id)

  const [rentalObject, setRentalObject] = useState<RentalObject | null>(null)
  const [spaces, setSpaces] = useState<RentalSpace[]>([])
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [selectedSpace, setSelectedSpace] = useState<RentalSpace | null>(null)
  const [saving, setSaving] = useState(false)
  const [spaceFormData, setSpaceFormData] = useState<Partial<RentalSpace>>({
    object_id: objectId,
    status: DEFAULT_SPACE_STATUS,
    photos: [],
  })

  const resetSpaceForm = useCallback(() => {
    setSelectedSpace(null)
    setSpaceFormData({
      object_id: objectId,
      status: DEFAULT_SPACE_STATUS,
      photos: [],
      floor: "",
      size: undefined,
      description: "",
    })
    setSaving(false)
  }, [objectId])

  const fetchSpaces = useCallback(async () => {
    if (!objectId || Number.isNaN(objectId)) {
      toast.error("Некорректный идентификатор объекта")
      return
    }

    try {
      await withLoading(async () => {
        const [objectData, objectSpaces] = await Promise.all([
          rentalObjectApi.getById(objectId),
          rentalSpaceApi.getByObjectId(objectId),
        ])
        setRentalObject(objectData)
        // Ensure objectSpaces is always an array
        setSpaces(Array.isArray(objectSpaces) ? objectSpaces : [])
      })
    } catch (error: any) {
      toast.error("Не удалось загрузить данные по помещениям", {
        description: error?.message ?? "Попробуйте повторить позже",
      })
      // Reset to empty array on error to prevent crashes
      setSpaces([])
    }
  }, [objectId, withLoading])

  useEffect(() => {
    fetchSpaces()
  }, [fetchSpaces])

  const spaceStats = useMemo(() => {
    // Defensive check: ensure spaces is always an array
    const spacesArray = Array.isArray(spaces) ? spaces : []
    
    const total = spacesArray.length
    const free = spacesArray.filter((space) => space.status === "FREE").length
    const occupied = total - free
    const totalArea = spacesArray.reduce((sum, space) => sum + (space.size ?? 0), 0)
    const maxFloor = spacesArray.reduce((max, space) => {
      const match = String(space.floor ?? "").match(/-?\d+/)
      const floor = match ? parseInt(match[0], 10) : 0
      return Number.isFinite(floor) ? Math.max(max, floor) : max
    }, 0)

    return { total, free, occupied, totalArea, maxFloor }
  }, [spaces])

  const getSpaceStatusBadge = useCallback((status: string) => {
    const variant = SPACE_STATUS_VARIANTS[status] ?? "secondary"
    const label = SPACE_STATUS_LABELS[status] ?? status
    return <Badge variant={variant}>{label}</Badge>
  }, [])

  const openSpaceEditor = useCallback(
    (space?: RentalSpace) => {
      if (space) {
        setSelectedSpace(space)
        setSpaceFormData({
          ...space,
          photos: [...(space.photos ?? [])],
        })
      } else {
        resetSpaceForm()
      }
      setIsEditorOpen(true)
    },
    [resetSpaceForm]
  )

  const handleEditorOpenChange = useCallback(
    (open: boolean) => {
      setIsEditorOpen(open)
      if (!open) {
        resetSpaceForm()
      }
    },
    [resetSpaceForm]
  )

  const handleSpaceInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { name, value } = event.target
      setSpaceFormData((prev) => ({
        ...prev,
        [name]: name === "size" ? (value ? Number(value) : undefined) : value,
      }))
    },
    []
  )

  const handleSpaceStatusChange = useCallback((value: string) => {
    setSpaceFormData((prev) => ({
      ...prev,
      status: value,
    }))
  }, [])

  const handleSpacePhotosChange = useCallback((links: string[]) => {
    setSpaceFormData((prev) => ({
      ...prev,
      photos: links,
    }))
  }, [])

  const sanitizeSpacePayload = useCallback(
    (data: Partial<RentalSpace>): Partial<RentalSpace> => {
      const { id: _id, object, views, created_at, updated_at, photos, ...rest } = data

      return {
        ...rest,
        object_id: objectId,
        size: rest.size ? Number(rest.size) : undefined,
        status: rest.status ?? DEFAULT_SPACE_STATUS,
        photos: (photos ?? []).map((url) => url.trim()).filter(Boolean),
      }
    },
    [objectId]
  )

  const handleSaveSpace = async () => {
    if (!spaceFormData.floor || !spaceFormData.floor.trim()) {
      toast.error("Укажите этаж помещения")
      return
    }

    if (!spaceFormData.size || Number(spaceFormData.size) <= 0) {
      toast.error("Площадь должна быть больше нуля")
      return
    }

    try {
      setSaving(true)
      const payload = sanitizeSpacePayload(spaceFormData)

      if (selectedSpace) {
        await rentalSpaceApi.update(selectedSpace.id, payload)
        toast.success("Помещение обновлено")
      } else {
        await rentalSpaceApi.create(
          payload as Omit<RentalSpace, "id" | "created_at" | "updated_at">
        )
        toast.success("Помещение создано")
      }

      await fetchSpaces()
      handleEditorOpenChange(false)
    } catch (error: any) {
      toast.error("Не удалось сохранить помещение", {
        description: error?.message ?? "Попробуйте повторить позже",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteSpace = useCallback(async (spaceId: number) => {
    if (!confirm("Удалить это помещение?")) return

    try {
      await rentalSpaceApi.delete(spaceId)
      setSpaces((prev) => prev.filter((space) => space.id !== spaceId))
      toast.success("Помещение удалено")
    } catch (error: any) {
      toast.error("Не удалось удалить помещение", {
        description: error?.message ?? "Попробуйте повторить позже",
      })
    }
  }, [])

  const columns = useMemo<ColumnDef<RentalSpace>[]>(
    () => [
      {
        id: "select",
        header: ({ table }) => (
          <div className="flex items-center justify-center">
            <Checkbox
              checked={
                table.getIsAllPageRowsSelected() ||
                (table.getIsSomePageRowsSelected() && "indeterminate")
              }
              onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
              aria-label="Выбрать все"
            />
          </div>
        ),
        cell: ({ row }) => (
          <div className="flex items-center justify-center">
            <Checkbox
              checked={row.getIsSelected()}
              onCheckedChange={(value) => row.toggleSelected(!!value)}
              aria-label="Выбрать строку"
            />
          </div>
        ),
        enableSorting: false,
        enableHiding: false,
      },
      {
        accessorKey: "id",
        header: "ID",
        cell: ({ row }) => <div className="font-medium">#{row.original.id}</div>,
      },
      {
        accessorKey: "floor",
        header: "Этаж",
        cell: ({ row }) => <span>{row.original.floor || "—"}</span>,
      },
      {
        accessorKey: "size",
        header: "Площадь, м²",
        cell: ({ row }) => (
          <span className="font-medium">{row.original.size?.toLocaleString("ru-RU") ?? "—"}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Статус",
        cell: ({ row }) => getSpaceStatusBadge(row.original.status ?? ""),
      },
      {
        accessorKey: "photos",
        header: "Фотографии",
        cell: ({ row }) => {
          const photos = row.original.photos ?? []
          if (photos.length === 0) {
            return <span className="text-sm text-muted-foreground">—</span>
          }

          return (
            <div className="flex flex-col gap-1 text-sm">
              <a
                href={photos[0]}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                <IconLink className="h-3.5 w-3.5" />
                Первое фото
              </a>
              {photos.length > 1 && (
                <span className="text-xs text-muted-foreground">+{photos.length - 1} дополнительно</span>
              )}
            </div>
          )
        },
      },
      {
        accessorKey: "description",
        header: "Описание",
        cell: ({ row }) => {
          const description = row.original.description || "—"
          return (
            <div 
              className="max-w-xs text-sm text-muted-foreground"
              title={description !== "—" ? description : undefined}
            >
              <span className="line-clamp-2 break-words">
                {description}
              </span>
            </div>
          )
        },
      },
      {
        accessorKey: "updated_at",
        header: "Обновлено",
        cell: ({ row }) => (
          <span className="text-sm">
            {new Date(row.original.updated_at).toLocaleString("ru-RU", {
              year: "numeric",
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        enableHiding: false,
        cell: ({ row }) => (
          <div className="flex items-start">
            <Button
              variant="outline"
              size="icon"
              onClick={() => openSpaceEditor(row.original)}
              aria-label="Редактировать помещение"
            >
              <IconEdit className="h-4 w-4" />
            </Button>
          </div>
        ),
      },
    ],
    [getSpaceStatusBadge, handleDeleteSpace, openSpaceEditor]
  )

  const EditorFields = () => (
    <>
      <div className="grid gap-4 p-4">
        <div className="space-y-2">
          <Label htmlFor="floor">Этаж</Label>
          <Input
            id="floor"
            name="floor"
            placeholder="Например, 5 или 5-6"
            value={spaceFormData.floor ?? ""}
            onChange={handleSpaceInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="size">Площадь, м²</Label>
          <Input
            id="size"
            name="size"
            type="number"
            min={1}
            step="0.1"
            value={spaceFormData.size ?? ""}
            onChange={handleSpaceInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="status">Статус</Label>
          <Select value={spaceFormData.status ?? DEFAULT_SPACE_STATUS} onValueChange={handleSpaceStatusChange}>
            <SelectTrigger id="status">
              <SelectValue placeholder="Выберите статус" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="FREE">Свободно</SelectItem>
              <SelectItem value="RESERVED">Забронировано</SelectItem>
              <SelectItem value="OCCUPIED">Сдано</SelectItem>
              <SelectItem value="MAINTENANCE">На обслуживании</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="description">Описание</Label>
          <Textarea
            id="description"
            name="description"
            placeholder="Кратко опишите особенности помещения"
            value={spaceFormData.description ?? ""}
            onChange={handleSpaceInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            rows={4}
          />
        </div>
        <PhotoLinksEditor
          label="Фотографии"
          description="Добавьте ссылки на фотографии помещения. Первое фото используется как обложка."
          value={spaceFormData.photos ?? []}
          onChange={handleSpacePhotosChange}
          addButtonLabel="Добавить фото"
        />
      </div>
    </>
  )

  const FooterButtons = () => (
    <>
      <Button onClick={handleSaveSpace} disabled={saving}>
        {saving ? "Сохранение..." : "Сохранить"}
      </Button>
      {selectedSpace && (
        <Button
          variant="outline"
          onClick={() => handleDeleteSpace(selectedSpace.id)}
          className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600"
        >
          Удалить
        </Button>
      )}
    </>
  )

  const renderEditor = () => {

    if (isMobile) {
      return (
        <Drawer open={isEditorOpen} onOpenChange={handleEditorOpenChange}>
          <DrawerContent className="p-0">
            <DrawerHeader>
              <DrawerTitle>{selectedSpace ? 'Edit Space' : 'Create Space'}</DrawerTitle>
            </DrawerHeader>
            <div className="overflow-y-auto max-h-[calc(100dvh-4.5rem)] pb-[50dvh]">
              {EditorFields()}
            </div>
            <DrawerFooter>
              <FooterButtons />
            </DrawerFooter>
          </DrawerContent>
        </Drawer>
      )
    }

    return (
      <Sheet open={isEditorOpen} onOpenChange={handleEditorOpenChange}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{selectedSpace ? 'Edit Space' : 'Create Space'}</SheetTitle>
            <SheetDescription>
              Заполните данные о помещении и добавьте ссылки на фотографии.
            </SheetDescription>
          </SheetHeader>
          {EditorFields()}
          <SheetFooter>
            <FooterButtons />
          </SheetFooter>
        </SheetContent>
      </Sheet>
    )
  }

  if (Number.isNaN(objectId)) {
    return (
      <div className="flex min-h-screen flex-col">
        <AppSidebar />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 items-center justify-center p-8">
            <Card className="max-w-md">
              <CardHeader>
                <CardTitle>Объект не найден</CardTitle>
                <CardDescription>
                  Проверьте корректность ссылки или вернитесь на страницу со списком бизнес-центров.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" onClick={() => router.push("/spaces")}>Вернуться к списку</Button>
              </CardContent>
            </Card>
          </div>
          <Toaster />
        </SidebarInset>
      </div>
    )
  }

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">

          <PageHeader
            title={rentalObject?.name ?? "Помещения"}
            description={
              rentalObject?.address
                ? `Управление помещениями объектa: ${rentalObject.address}`
                : "Управление помещениями объекта"
            }
            buttonText="Добавить помещение"
            buttonIcon={<IconPlus className="h-4 w-4" />}
            onButtonClick={() => openSpaceEditor()}
          />

          <Card className="overflow-hidden">
            {rentalObject?.photos && rentalObject.photos.length > 0 ? (
              <div
                className="h-48 w-full bg-cover bg-center"
                style={{ backgroundImage: `url(${rentalObject.photos[0]})` }}
              />
            ) : (
              <div className="flex h-48 w-full items-center justify-center bg-muted">
                <span className="text-sm text-muted-foreground">Фотография обложки не добавлена</span>
              </div>
            )}
            <CardHeader>
              <CardTitle>{rentalObject?.name ?? "—"}</CardTitle>
              <CardDescription>{rentalObject?.description || "Описание отсутствует"}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Адрес</div>
                  <div className="text-sm font-medium">{rentalObject?.address ?? "—"}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Всего помещений</div>
                  <div className="text-xl font-semibold">{spaceStats.total}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Свободно</div>
                  <div className="text-xl font-semibold text-emerald-600">{spaceStats.free}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Общая площадь</div>
                  <div className="text-xl font-semibold">{spaceStats.totalArea.toLocaleString("ru-RU")} м²</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <DataTable
                data={spaces}
                columns={columns}
                loading={loading}
                loadingMessage="Загрузка помещений..."
              />
        </div>
      </SidebarInset>

      {renderEditor()}
      <Toaster />
    </>
  )
}

