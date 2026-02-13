"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset } from "@/components/ui/sidebar"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerFooter } from "@/components/ui/drawer"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useIsMobile } from "@/hooks/use-mobile"
import { IconPlus, IconTicket, IconEdit, IconEye, IconClock, IconCheck, IconX, IconAlertTriangle, IconTrash } from "@tabler/icons-react"
import { ServiceTicket, User, TICKET_STATUS, TICKET_STATUS_LABELS_RU, TICKET_PRIORITY, TICKET_PRIORITY_LABELS_RU } from '@/types'
import { serviceTicketApi, userApi } from '@/lib/api'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
import { PageHeader } from "@/components/page-header"
import { useLoading } from "@/hooks/use-loading"
import { DataPicker, DataPickerField } from '@/components/data-picker'

export default function ServiceTicketsPage() {
  const isMobile = useIsMobile()
  const [tickets, setTickets] = useState<ServiceTicket[]>([])
  const [users, setUsers] = useState<User[]>([])
  const { loading, withLoading } = useLoading(true)
  const [selectedTicket, setSelectedTicket] = useState<ServiceTicket | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState<Partial<ServiceTicket>>({})
  const [isUserPickerOpen, setIsUserPickerOpen] = useState(false)

  // Field configuration for User DataPicker
  const userFields: DataPickerField[] = [
    { key: 'first_name', label: 'Имя', searchable: true },
    { key: 'last_name', label: 'Фамилия', searchable: true },
    { key: 'username', label: 'Username', searchable: true },
    { key: 'email', label: 'Email', searchable: true },
    { key: 'id', label: 'ID', render: (value) => <span className="text-right">#{value}</span> }
  ]

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    await withLoading(async () => {
      const [allTickets, allUsers] = await Promise.all([
        serviceTicketApi.getAll(),
        userApi.getAll(),
      ])
      const ticketsWithUsers = allTickets.map(ticket => ({
        ...ticket,
        user: allUsers.find(u => u.id === ticket.user_id) || { first_name: 'Unknown', last_name: '', username: '' } as User
      }))
      setTickets(ticketsWithUsers)
      setUsers(allUsers)
    }).catch((error: any) => {
      toast.error('Failed to fetch data', { description: error.message || 'Unknown error' })
      console.error(error)
    })
  }


  const handleOpen = (ticket?: ServiceTicket) => {
    setSelectedTicket(ticket ?? null)
    setFormData(ticket ?? {})
    setIsOpen(true)
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedTicket(null)
    setFormData({})
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSelectChange = (name: string, value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    await withLoading(async () => {
      if (selectedTicket) {
        // Exclude created_at, updated_at, id and nested user from update data to avoid validation issues
        const { created_at, updated_at, user, id, ...rest } = formData as any
        const updateData: any = { ...rest }

        // Normalise numeric fields before sending to API
        if (typeof updateData.user_id === "string") {
          const num = parseInt(updateData.user_id, 10)
          if (!Number.isNaN(num)) updateData.user_id = num
          else delete updateData.user_id
        }
        if (typeof updateData.priority === "string") {
          const num = parseInt(updateData.priority, 10)
          if (!Number.isNaN(num)) updateData.priority = num
          else delete updateData.priority
        }

        const updated = await serviceTicketApi.update(selectedTicket.id, updateData)
        setTickets(prev => prev.map(t => t.id === updated.id ? updated : t))
        toast.success('Ticket updated', { description: 'Ticket updated successfully.' })
      } else {
        const { created_at, updated_at, user, id, ...rest } = formData as any
        const payload: any = { ...rest }
        // Ensure required backend fields have safe defaults
        if (!payload.ddid) payload.ddid = '0000-0000-0000'
        if (typeof payload.user_id === 'string') {
          const num = parseInt(payload.user_id, 10)
          if (!Number.isNaN(num)) payload.user_id = num
        }
        if (typeof payload.priority === 'string') {
          const num = parseInt(payload.priority, 10)
          if (!Number.isNaN(num)) payload.priority = num
        }
        const created = await serviceTicketApi.create(payload as Omit<ServiceTicket, 'id' | 'created_at' | 'updated_at'>)
        created.user = users.find(u => u.id === created.user_id) || { first_name: 'Unknown', last_name: '', username: '' } as User
        setTickets(prev => [...prev, created])
        toast.success('Ticket created', { description: 'Ticket created successfully.' })
      }
      handleClose()
      fetchData() // Refresh
    }).catch((error: any) => {
      toast.error('Failed to save ticket', { description: error.message })
      console.error(error)
    })
  }

  const handleDelete = async () => {
    if (!selectedTicket) return
    if (confirm('Are you sure you want to delete this ticket?')) {
      await withLoading(async () => {
        await serviceTicketApi.delete(selectedTicket.id)
        setTickets(prev => prev.filter(t => t.id !== selectedTicket.id))
        toast.success('Ticket deleted', { description: 'Ticket deleted successfully.' })
        handleClose()
      }).catch((error: any) => {
        toast.error('Failed to delete ticket', { description: error.message })
        console.error(error)
      })
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case TICKET_STATUS.NEW: return <Badge variant="destructive"><IconX className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.NEW]}</Badge>
      case TICKET_STATUS.ACCEPTED: return <Badge variant="secondary"><IconClock className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ACCEPTED]}</Badge>
      case TICKET_STATUS.ASSIGNED: return <Badge variant="default"><IconAlertTriangle className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.ASSIGNED]}</Badge>
      case TICKET_STATUS.COMPLETED: return <Badge variant="outline"><IconCheck className="h-3 w-3 mr-1" />{TICKET_STATUS_LABELS_RU[TICKET_STATUS.COMPLETED]}</Badge>
      default: return <Badge variant="outline">Неизвестно</Badge>
    }
  }

  const getPriorityBadge = (priority: number) => {
    switch (priority) {
      case TICKET_PRIORITY.LOW: return <Badge variant="outline">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.LOW]}</Badge>
      case TICKET_PRIORITY.MEDIUM: return <Badge variant="secondary">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.MEDIUM]}</Badge>
      case TICKET_PRIORITY.HIGH: return <Badge variant="destructive">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.HIGH]}</Badge>
      case TICKET_PRIORITY.CRITICAL: return <Badge className="bg-red-600 hover:bg-red-700">{TICKET_PRIORITY_LABELS_RU[TICKET_PRIORITY.CRITICAL]}</Badge>
      default: return <Badge variant="outline">Неопределен</Badge>
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }


  const FooterButtons = () => (
    <>
      <Button onClick={handleSave}>Save</Button>
      {selectedTicket && (
        <Button variant="outline" onClick={handleDelete} className="border-red-500 text-red-500 hover:bg-red-50 hover:text-red-600">
          Удалить
        </Button>
      )}
    </>
  )

  const EditContent = () => (
    <>
      <div className="grid gap-4 p-4">
        <div className="space-y-2">
          <Label htmlFor="description">Description</Label>
          <Textarea id="description" name="description" value={formData.description ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="location">Location</Label>
          <Input id="location" name="location" value={formData.location ?? ''} onChange={handleInputChange} />
        </div>
        <div className="flex gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            <Label htmlFor="priority">Priority</Label>
            <Select value={formData.priority?.toString() ?? ''} onValueChange={(v) => handleSelectChange('priority', v)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={String(TICKET_PRIORITY.LOW)}>Low</SelectItem>
                <SelectItem value={String(TICKET_PRIORITY.MEDIUM)}>Medium</SelectItem>
                <SelectItem value={String(TICKET_PRIORITY.HIGH)}>High</SelectItem>
                <SelectItem value={String(TICKET_PRIORITY.CRITICAL)}>Critical</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 flex-1 min-w-0">
            <Label htmlFor="status">Status</Label>
            <Select value={formData.status ?? ''} onValueChange={(v) => handleSelectChange('status', v)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TICKET_STATUS.NEW}>New</SelectItem>
                <SelectItem value={TICKET_STATUS.ACCEPTED}>Accepted</SelectItem>
                <SelectItem value={TICKET_STATUS.ASSIGNED}>Assigned</SelectItem>
                <SelectItem value={TICKET_STATUS.COMPLETED}>Completed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-2">
          <Label htmlFor="user_id">User</Label>
          <DataPicker
            title="Выбор пользователя"
            description="Найдите пользователя по имени, email или username и кликните, чтобы выбрать."
            data={users}
            fields={userFields}
            value={formData.user_id}
            displayValue={
              formData.user_id
                ? (() => {
                    const user = users.find(u => u.id === formData.user_id)
                    return user ? `${user.last_name} ${user.first_name} (@${user.username})` : `User #${formData.user_id}`
                  })()
                : undefined
            }
            placeholder="Не назначен"
            onSelect={(user: User) => setFormData(prev => ({ ...prev, user_id: user.id }))}
            open={isUserPickerOpen}
            onOpenChange={setIsUserPickerOpen}
          />
        </div>
      </div>
    </>
  )

  // Add columns
  const columns: ColumnDef<ServiceTicket>[] = [
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
            aria-label="Select all"
          />
        </div>
      ),
      cell: ({ row }) => (
        <div className="flex items-center justify-center">
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
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
      accessorKey: "ticket",
      header: "Заявка",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">{row.original.description || 'No description'}</div>
          <div className="text-sm text-muted-foreground">{row.original.location || 'No location'}</div>
        </div>
      ),
    },
    {
      accessorKey: "user",
      header: "Пользователь",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">
            {row.original.user?.last_name} {row.original.user?.first_name}
          </div>
          <div className="text-sm text-muted-foreground">
            @{row.original.user?.username}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Статус",
      cell: ({ row }) => getStatusBadge(row.original.status),
    },
    {
      accessorKey: "priority",
      header: "Приоритет",
      cell: ({ row }) => getPriorityBadge(row.original.priority),
    },
    {
      accessorKey: "category",
      header: "Категория",
      cell: ({ row }) => <Badge variant="outline">{row.original.category || 'No category'}</Badge>,
    },
    {
      accessorKey: "created",
      header: "Создана",
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="flex items-center space-x-2 justify-end pr-2">
          <Button variant="outline" size="sm" onClick={() => handleOpen(row.original)}>
            <IconEdit className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ]

  return (
    <>
      <AppSidebar />
      <SidebarInset>
        <SiteHeader />
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
          <PageHeader
            title="Заявки на обслуживание"
            description="Управление заявками на техническое обслуживание"
            buttonText="Создать заявку"
            onButtonClick={() => handleOpen()}
            buttonIcon={<IconPlus className="h-4 w-4 mr-2" />}
          />

          <DataTable data={tickets} columns={columns} loading={loading} loadingMessage="Загрузка заявок..." />
        </div>
      </SidebarInset>

      {isMobile ? (
        <Drawer open={isOpen} onOpenChange={setIsOpen}>
          <DrawerContent className="p-0">
            <DrawerHeader>
              <DrawerTitle>{selectedTicket ? 'Edit Ticket' : 'Create Ticket'}</DrawerTitle>
            </DrawerHeader>
            <div className="overflow-y-auto max-h-[calc(100dvh-4.5rem)] pb-[50dvh]">
              {EditContent()}
            </div>
            <DrawerFooter>
              <FooterButtons />
            </DrawerFooter>
          </DrawerContent>
        </Drawer>
      ) : (
        <Sheet open={isOpen} onOpenChange={setIsOpen}>
          <SheetContent side="right">
            <SheetHeader>
              <SheetTitle>{selectedTicket ? 'Edit Ticket' : 'Create Ticket'}</SheetTitle>
              <SheetDescription>
                {selectedTicket ? 'Edit service ticket information and status.' : 'Create a new service ticket for user support.'}
              </SheetDescription>
            </SheetHeader>
            {EditContent()}
            <SheetFooter>
              <FooterButtons />
            </SheetFooter>
          </SheetContent>
        </Sheet>
      )}
      <Toaster />
    </>
  )
} 