"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  IconBuildingSkyscraper,
  IconChevronRight,
  IconEdit,
  IconMapPin,
  IconPhoto,
  IconPlus,
} from "@tabler/icons-react"
import { toast } from "sonner"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { PageHeader } from "@/components/page-header"
import { PhotoLinksEditor } from "@/components/photo-links-editor"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Drawer, DrawerContent, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { SidebarInset } from "@/components/ui/sidebar"
import { Textarea } from "@/components/ui/textarea"
import { Toaster } from "@/components/ui/sonner"
import { useIsMobile } from "@/hooks/use-mobile"
import { rentalObjectApi, rentalSpaceApi } from "@/lib/api"
import { RentalObject, RentalSpace } from "@/types"
import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"

const PAGE_SIZE = 10

interface BusinessCenterWithStats extends RentalObject {
  totalSpaces: number
  availableSpaces: number
  occupiedSpaces: number
  floors: number
  totalArea: number
}

type StatusVariant = "default" | "secondary" | "outline" | "destructive"

export default function SpacesPage() {
  const router = useRouter()
  const isMobile = useIsMobile()

  const [businessCenters, setBusinessCenters] = useState<BusinessCenterWithStats[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedCenter, setSelectedCenter] = useState<BusinessCenterWithStats | null>(null)
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<Partial<RentalObject>>({
    status: "ACTIVE",
    photos: [],
  })

  const resetForm = useCallback(() => {
    setSelectedCenter(null)
    setFormData({ status: "ACTIVE", photos: [] })
    setSaving(false)
  }, [])

  const parseFloorNumber = useCallback((value: RentalSpace["floor"]) => {
    if (value === null || value === undefined) return 0
    const match = String(value).match(/-?\d+/)
    return match ? parseInt(match[0], 10) : 0
  }, [])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [objects, spaces] = await Promise.all([
        rentalObjectApi.getAll(),
        rentalSpaceApi.getAll(),
      ])

      const centersWithStats = objects.map((object) => {
        const spacesForObject = spaces.filter((space) => space.object_id === object.id)
        const availableSpaces = spacesForObject.filter((space) => space.status === "FREE").length
        const occupiedSpaces = spacesForObject.length - availableSpaces
        const floors = spacesForObject.reduce((maxFloor, space) => {
          const floorNumber = parseFloorNumber(space.floor)
          return Number.isFinite(floorNumber) ? Math.max(maxFloor, floorNumber) : maxFloor
        }, 0)
        const totalArea = spacesForObject.reduce((sum, space) => sum + (space.size ?? 0), 0)

        return {
          ...object,
          totalSpaces: spacesForObject.length,
          availableSpaces,
          occupiedSpaces,
          floors,
          totalArea,
        }
      })

      setBusinessCenters(centersWithStats)
    } catch (error: any) {
      toast.error("Не удалось загрузить данные", {
        description: error?.message ?? "Попробуйте повторить чуть позже",
      })
    } finally {
      setLoading(false)
    }
  }, [parseFloorNumber])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // DataTable will handle search, sorting, and pagination

  const getOccupancyRate = (occupied: number, total: number) => {
    if (total <= 0) return 0
    return Math.round((occupied / total) * 100)
  }

  // Occupancy badges are removed per new UI

  const getStatusVariant = (status?: string): StatusVariant => {
    switch (status) {
      case "ACTIVE":
        return "default"
      case "INACTIVE":
        return "secondary"
      case "ARCHIVED":
        return "outline"
      default:
        return "secondary"
    }
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return "—"
    return new Date(dateString).toLocaleDateString("ru-RU", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  const handleEditorOpenChange = (open: boolean) => {
    setIsEditorOpen(open)
  }

  const handleOpen = (center?: BusinessCenterWithStats) => {
    if (center) {
      const {
        totalSpaces,
        availableSpaces,
        occupiedSpaces,
        floors,
        totalArea,
        spaces,
        users,
        photos,
        ...rest
      } = center

      setSelectedCenter(center)
      setFormData({
        ...rest,
        status: rest.status ?? "ACTIVE",
        photos: [...(photos ?? [])],
      })
    } else {
      resetForm()
    }
    setIsEditorOpen(true)
  }

  const handleClose = () => {
    setIsEditorOpen(false)
    resetForm()
  }

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = event.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleStatusChange = (value: string) => {
    setFormData((prev) => ({
      ...prev,
      status: value,
    }))
  }

  const handlePhotosChange = (links: string[]) => {
    setFormData((prev) => ({
      ...prev,
      photos: links,
    }))
  }

  const sanitizePayload = (data: Partial<RentalObject>): Partial<RentalObject> => {
    const {
      created_at,
      updated_at,
      spaces,
      users,
      id: _id,
      photos,
      ...rest
    } = data

    return {
      ...rest,
      status: rest.status ?? "ACTIVE",
      photos: (photos ?? []).map((url) => url.trim()).filter(Boolean),
    }
  }

  const handleSave = async () => {
    const payload = sanitizePayload(formData)

    if (!payload.name || !payload.name.trim()) {
      toast.error("Укажите название бизнес-центра")
      return
    }

    if (!payload.address || !payload.address.trim()) {
      toast.error("Укажите адрес бизнес-центра")
      return
    }

    try {
      setSaving(true)
      if (selectedCenter) {
        await rentalObjectApi.update(selectedCenter.id, payload)
        toast.success("Бизнес-центр обновлён")
      } else {
        await rentalObjectApi.create(
          payload as Omit<RentalObject, "id" | "created_at" | "updated_at">
        )
        toast.success("Бизнес-центр создан")
      }

      await fetchData()
      handleClose()
    } catch (error: any) {
      toast.error("Не удалось сохранить бизнес-центр", {
        description: error?.message ?? "Попробуйте повторить позже",
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (center: BusinessCenterWithStats, event?: React.MouseEvent) => {
    event?.stopPropagation()
    if (!confirm(`Удалить бизнес-центр "${center.name}"?`)) return

    try {
      await rentalObjectApi.delete(center.id)
      setBusinessCenters((prev) => prev.filter((item) => item.id !== center.id))
      toast.success("Бизнес-центр удалён")
    } catch (error: any) {
      toast.error("Не удалось удалить бизнес-центр", {
        description: error?.message ?? "Попробуйте повторить позже",
      })
    }
  }

  const EditorFields = () => (
    <>
      <div className="grid gap-4 p-4">
        <div className="space-y-2">
          <Label htmlFor="name">Название</Label>
          <Input
            id="name"
            name="name"
            placeholder="Например, БЦ Nord"
            value={formData.name ?? ""}
            onChange={handleInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="address">Адрес</Label>
          <Input
            id="address"
            name="address"
            placeholder="Город, улица, дом"
            value={formData.address ?? ""}
            onChange={handleInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="description">Описание</Label>
          <Textarea
            id="description"
            name="description"
            placeholder="Краткое описание инфраструктуры и преимуществ"
            value={formData.description ?? ""}
            onChange={handleInputChange}
            onKeyDown={(e) => e.stopPropagation()}
            onFocus={(e) => e.stopPropagation()}
            rows={4}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="status">Статус</Label>
          <Select value={formData.status ?? "ACTIVE"} onValueChange={handleStatusChange}>
            <SelectTrigger id="status">
              <SelectValue placeholder="Выберите статус" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ACTIVE">Активен</SelectItem>
              <SelectItem value="INACTIVE">Неактивен</SelectItem>
              <SelectItem value="ARCHIVED">Архив</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <PhotoLinksEditor
          label="Фотографии"
          description="Добавьте ссылки на изображения для обложки и галереи бизнес-центра. Первое фото будет использовано в качестве обложки."
          value={formData.photos ?? []}
          onChange={handlePhotosChange}
          addButtonLabel="Добавить фото"
        />
      </div>
    </>
  )

  const FooterButtons = () => (
    <>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? "Сохранение..." : "Сохранить"}
      </Button>
      {selectedCenter && (
        <Button
          variant="outline"
          onClick={() => handleDelete(selectedCenter)}
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
              <DrawerTitle>{selectedCenter ? 'Edit Center' : 'Create Center'}</DrawerTitle>
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
            <SheetTitle>{selectedCenter ? 'Edit Center' : 'Create Center'}</SheetTitle>
            <SheetDescription>
              Заполните информацию о бизнес-центре и добавьте ссылки на фотографии.
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

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">
          <PageHeader
            title="Бизнес-центры"
            description="Управляйте объектами и просматривайте доступные помещения"
            buttonText="Добавить центр"
            buttonIcon={<IconPlus className="h-4 w-4" />}
            onButtonClick={() => handleOpen()}
          />
          {/* DataTable with card view */}
          <DataTable<BusinessCenterWithStats>
            data={businessCenters}
            columns={(
              [
                { accessorKey: 'id', header: 'ID' },
                { accessorKey: 'name', header: 'Название' },
                { accessorKey: 'address', header: 'Адрес' },
                { accessorKey: 'status', header: 'Статус' },
                { accessorKey: 'updated_at', header: 'Обновлено' },
              ] as unknown as ColumnDef<BusinessCenterWithStats>[]
            )}
            loading={loading}
            view="cards"
            cardsClassName="md:grid-cols-2 xl:grid-cols-3"
            renderCard={(row) => {
              const center = row.original as BusinessCenterWithStats
              const occupancyRate = getOccupancyRate(center.occupiedSpaces, center.totalSpaces)
              return (
                <Card
                  key={center.id}
                  className="overflow-hidden transition-shadow hover:shadow-lg"
                  onClick={() => router.push(`/spaces/${center.id}`)}
                >
                  <div className="relative aspect-video w-full bg-muted">
                    {center.photos && center.photos.length > 0 ? (
                      <div
                        className="h-full w-full bg-cover bg-center"
                        style={{ backgroundImage: `url(${center.photos[0]})` }}
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
                        <IconBuildingSkyscraper className="h-12 w-12 text-gray-400" />
                      </div>
                    )}

                    {center.photos && center.photos.length > 0 && (
                      <div className="absolute right-3 top-3 flex items-center gap-1 rounded-full bg-black/60 px-2 py-1 text-xs text-white">
                        <IconPhoto className="h-3 w-3" />
                        {center.photos.length}
                      </div>
                    )}
                  </div>

                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <CardTitle className="text-xl">{center.name}</CardTitle>
                        <div className="flex items-center text-sm text-muted-foreground">
                          <IconMapPin className="mr-1 h-4 w-4" />
                          {center.address}
                        </div>
                      </div>
                      <div className="flex items-center gap-2" onClick={(event) => event.stopPropagation()}>

                        <Button
                          variant="outline"
                          size="icon"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleOpen(center)
                          }}
                          aria-label="Редактировать бизнес-центр"
                        >
                          <IconEdit className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    {center.description && (
                      <CardDescription className="line-clamp-2">
                        {center.description}
                      </CardDescription>
                    )}
                  </CardHeader>

                  <CardContent>
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span>Загрузка помещений</span>
                          <span>{occupancyRate}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-muted">
                          <div
                            className="h-2 rounded-full bg-primary"
                            style={{ width: `${occupancyRate}%` }}
                          />
                        </div>
                        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                          <span>{center.occupiedSpaces} из {center.totalSpaces} помещений занято</span>
                          <span>Общая площадь: {center.totalArea.toLocaleString("ru-RU")} м²</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-sm text-muted-foreground">
                        <span>Обновлено: {formatDate(center.updated_at)}</span>
                      </div>

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="w-full gap-2"
                        onClick={(event) => {
                          event.stopPropagation()
                          router.push(`/spaces/${center.id}`)
                        }}
                      >
                        Управлять площадями
                        <IconChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )
            }}
          />
        </div>
      </SidebarInset>

      {renderEditor()}
      <Toaster />
    </>
  )
} 