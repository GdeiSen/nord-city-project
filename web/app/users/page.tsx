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
import { IconPlus, IconUserPlus, IconEdit, IconTrash, IconEye, IconX, IconUser } from "@tabler/icons-react"
import { User, USER_ROLES, UserRole, ROLE_LABELS, ROLE_BADGE_VARIANTS, RentalObject } from '@/types'
import { userApi, rentalObjectApi } from '@/lib/api'
import { DataPicker, DataPickerField } from '@/components/data-picker'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingWrapper } from "@/components/ui/loading-wrapper"
import { useLoading } from "@/hooks/use-loading"
import { PageHeader } from "@/components/page-header"

export default function UsersPage() {
  const isMobile = useIsMobile()
  const [users, setUsers] = useState<User[]>([])
  const { loading, withLoading } = useLoading(true)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState<Partial<User>>({})

  // Data for object picker
  const [objects, setObjects] = useState<RentalObject[]>([])
  const [isObjectPickerOpen, setIsObjectPickerOpen] = useState(false)

  // Field configurations for DataPicker
  const objectFields: DataPickerField[] = [
    { key: 'name', label: 'Название', searchable: true },
    { key: 'address', label: 'Адрес', searchable: true },
    { key: 'id', label: 'ID', render: (value) => <span className="text-right">{value}</span> }
  ]

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    await withLoading(async () => {
      const allUsers: User[] = await userApi.getAll()
      setUsers(allUsers)
    }).catch((error: any) => {
      toast.error('Failed to fetch users', { description: error.message || 'Unknown error' })
      console.error(error)
    })
  }

  useEffect(() => {
    // fetch available objects for selection
    const fetchObjects = async () => {
      try {
        const allObjects = await rentalObjectApi.getAll()
        setObjects(allObjects)
      } catch (error: any) {
        toast.error('Failed to fetch objects', { description: error.message || 'Unknown error' })
        console.error(error)
      }
    }
    fetchObjects()
  }, [])


  const handleOpen = (user?: User) => {
    setSelectedUser(user ?? null)
    setFormData(user ?? {})
    setIsOpen(true)
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedUser(null)
    setFormData({})
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSelectChange = (name: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [name]: name === 'role' ? parseInt(value) : value
    }))
  }

  const handleSave = async () => {
    await withLoading(async () => {
      if (selectedUser) {
        // Exclude id and timestamps from update data to avoid schema and datetime issues
        const { id, created_at, updated_at, ...updateData } = formData
        const updated = await userApi.update(selectedUser.id, updateData)
        setUsers(prev => prev.map(u => u.id === updated.id ? updated : u))
        toast.success('User updated', { description: 'User updated successfully.' })
      } else {
        const created = await userApi.create(formData as Omit<User, 'id' | 'created_at' | 'updated_at'>)
        setUsers(prev => [...prev, created])
        toast.success('User created', { description: 'User created successfully.' })
      }
      handleClose()
      fetchUsers() // Refresh
    }).catch((error: any) => {
      toast.error('Failed to save user', { description: error.message })
      console.error(error)
    })
  }

  const handleDelete = async () => {
    if (!selectedUser) return
    if (confirm('Are you sure you want to delete this user?')) {
      await withLoading(async () => {
        await userApi.delete(selectedUser.id)
        setUsers(prev => prev.filter(u => u.id !== selectedUser.id))
        toast.success('User deleted', { description: 'User deleted successfully.' })
        handleClose()
      }).catch((error: any) => {
        toast.error('Failed to delete user', { description: error.message })
        console.error(error)
      })
    }
  }

  const getRoleBadge = (role: number | undefined) => {
    if (role === undefined) {
      return <Badge variant="outline">Неопределен</Badge>
    }

    const roleKey = Object.values(USER_ROLES).find(r => r === role)
    if (!roleKey) {
      return <Badge variant="outline">Неизвестная роль</Badge>
    }

    return <Badge variant={ROLE_BADGE_VARIANTS[roleKey]}>{ROLE_LABELS[roleKey]}</Badge>
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }

  const FooterButtons = () => (
    <>
      <Button onClick={handleSave}>Save</Button>
      {selectedUser && selectedUser.role !== USER_ROLES.ADMIN && (
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
          <Label htmlFor="first_name">First Name</Label>
          <Input id="first_name" name="first_name" value={formData.first_name ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input id="last_name" name="last_name" value={formData.last_name ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="middle_name">Middle Name</Label>
          <Input id="middle_name" name="middle_name" value={formData.middle_name ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input id="username" name="username" value={formData.username ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" type="email" value={formData.email ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone_number">Phone</Label>
          <Input id="phone_number" name="phone_number" value={formData.phone_number ?? ''} onChange={handleInputChange} />
        </div>
        <div className="flex gap-4">
          <div className="space-y-2 flex-1 min-w-0">
            <Label htmlFor="role">Role</Label>
            <Select value={formData.role?.toString() ?? ''} onValueChange={(v) => handleSelectChange('role', v)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(USER_ROLES).map(([key, value]) => (
                  <SelectItem key={key} value={value.toString()}>
                    {ROLE_LABELS[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2 flex-1 min-w-0">
            <Label htmlFor="language_code">Language</Label>
            <Select value={formData.language_code ?? 'ru'} onValueChange={(v) => handleSelectChange('language_code', v)}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select language" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ru">Русский</SelectItem>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="kz">Қазақша</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        {/* Data pickers in one row */}
            <Label htmlFor="object_id">Object</Label>
            <DataPicker
              title="Выбор объекта"
              description="Найдите объект по названию или адресу и кликните, чтобы выбрать."
              data={objects}
              fields={objectFields}
              value={formData.object_id}
              displayValue={
                formData.object_id
                  ? (() => {
                      const obj = objects.find(o => o.id === formData.object_id)
                      return obj ? `${obj.name} (БЦ-${obj.id})` : `БЦ-${formData.object_id}`
                    })()
                  : undefined
              }
              placeholder="Не назначен"
              onSelect={(obj: RentalObject) => setFormData(prev => ({ ...prev, object_id: obj.id }))}
              open={isObjectPickerOpen}
              onOpenChange={setIsObjectPickerOpen}
            />
        <div className="space-y-2">
          <Label htmlFor="legal_entity">Legal entity</Label>
          <Input id="legal_entity" name="legal_entity" value={formData.legal_entity ?? ''} onChange={handleInputChange} />
        </div>
      </div>
    </>
  )

  const columns: ColumnDef<User>[] = [
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
      accessorKey: "user",
      accessorFn: (row) => `${row.last_name ?? ''} ${row.first_name ?? ''} ${row.middle_name ?? ''} @${row.username ?? ''}`.trim(),
      header: "Пользователь",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">
            {row.original.last_name} {row.original.first_name} {row.original.middle_name}
          </div>
          <div className="text-sm text-muted-foreground">
            @{row.original.username}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "contacts",
      accessorFn: (row) => `${row.email ?? ''} ${row.phone_number ?? ''}`.trim(),
      header: "Контакты",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="text-sm">
            {row.original.email}
          </div>
          <div className="text-sm text-muted-foreground">
            {row.original.phone_number}
          </div>
        </div>
      ),
    },
    {
      accessorKey: "role",
      header: "Роль",
      cell: ({ row }) => getRoleBadge(row.original.role),
    },
    {
      accessorKey: "object",
      accessorFn: (row) => (row.object_id ? `БЦ-${row.object_id}` : ''),
      header: "Объект",
      cell: ({ row }) => (
        row.original.object_id ? (
          <Badge variant="outline">БЦ-{row.original.object_id}</Badge>
        ) : (
          <span className="text-muted-foreground">Не назначен</span>
        )
      ),
    },
    {
      accessorKey: "legal_entity",
      header: "Юр. лицо",
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.legal_entity || <span className="text-muted-foreground">Не указано</span>}
        </div>
      ),
    },
    {
      accessorKey: "created",
      accessorFn: (row) => new Date(row.created_at).toISOString(),
      header: "Создан",
      cell: ({ row }) => (
        <div className="text-sm">
          {formatDate(row.original.created_at)}
        </div>
      ),
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
            title="Пользователи"
            description="Управление пользователями системы"
            // buttonText="Добавить пользователя"
            // onButtonClick={() => handleOpen()}
            buttonIcon={<IconUserPlus className="h-4 w-4 mr-2" />}
          />

          <DataTable data={users} columns={columns} loading={loading} loadingMessage="Загрузка пользователей..." />
        </div>
      </SidebarInset>

      {isMobile ? (
        <Drawer open={isOpen} onOpenChange={setIsOpen}>
          <DrawerContent className="p-0">
            <DrawerHeader>
              <DrawerTitle>{selectedUser ? 'Edit User' : 'Create User'}</DrawerTitle>
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
              <SheetTitle>{selectedUser ? 'Edit User' : 'Create User'}</SheetTitle>
              <SheetDescription>
                {selectedUser ? 'Edit user information and permissions.' : 'Create a new user account with role and permissions.'}
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
