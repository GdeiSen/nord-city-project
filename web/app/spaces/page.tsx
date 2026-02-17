"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
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
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { rentalObjectApi, rentalSpaceApi } from "@/lib/api"
import { formatDate } from "@/lib/date-utils"
import { RentalObject, RentalSpace } from "@/types"
import { DataTable } from "@/components/data-table"
import { ColumnDef } from "@tanstack/react-table"
import { useCanEdit } from "@/hooks"

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
  const canEdit = useCanEdit()

  const [businessCenters, setBusinessCenters] = useState<BusinessCenterWithStats[]>([])
  const [loading, setLoading] = useState(true)

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

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 min-w-0 space-y-4 p-4 pt-6 md:p-8">
          <PageHeader
            title="Бизнес-центры"
            description="Управляйте объектами и просматривайте доступные помещения"
            buttonText={canEdit ? "Добавить центр" : undefined}
            buttonIcon={canEdit ? <IconPlus className="h-4 w-4" /> : undefined}
            onButtonClick={canEdit ? () => router.push("/spaces/edit") : undefined}
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
                      {canEdit && (
                        <div className="flex items-center gap-2" onClick={(event) => event.stopPropagation()}>
                          <Button variant="outline" size="icon" asChild aria-label="Редактировать бизнес-центр">
                            <Link href={`/spaces/edit/${center.id}`}>
                              <IconEdit className="h-4 w-4" />
                            </Link>
                          </Button>
                        </div>
                      )}
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
                        <span>Обновлено: {formatDate(center.updated_at ?? "", { includeTime: false })}</span>
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
      <Toaster />
    </>
  )
} 