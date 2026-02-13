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
import { IconMessageCircle, IconEdit, IconEye, IconStar, IconStarFilled, IconTrendingUp, IconTrendingDown, IconTrash } from "@tabler/icons-react"
import { Feedback, User } from '@/types'
import { feedbackApi, userApi } from '@/lib/api'
import { Toaster } from "@/components/ui/sonner"
import { toast } from "sonner"
import { ColumnDef } from "@tanstack/react-table"
import { DataTable } from "@/components/data-table"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingWrapper } from "@/components/ui/loading-wrapper"
import { useLoading } from "@/hooks/use-loading"
import { PageHeader } from "@/components/page-header"

/**
 * Feedbacks management page component
 * 
 * Displays a table of all user feedback with filtering, search, and management capabilities.
 * Allows administrators to view, respond to, and analyze user feedback.
 * 
 * @returns JSX.Element
 */
export default function FeedbacksPage() {
  const isMobile = useIsMobile()
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([])
  const [users, setUsers] = useState<User[]>([])
  const { loading, withLoading } = useLoading(true)
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [formData, setFormData] = useState<Partial<Feedback>>({})

  useEffect(() => {
    const fetchData = async () => {
      await withLoading(async () => {
        const [allFeedbacks, allUsers] = await Promise.all([
          feedbackApi.getAll(),
          userApi.getAll(),
        ])
        const feedbacksWithUsers = allFeedbacks.map(f => ({
          ...f,
          user: allUsers.find(u => u.id === f.user_id) || { first_name: '', last_name: '', username: '' } as User
        }))
        setFeedbacks(feedbacksWithUsers)
        setUsers(allUsers)
      }).catch((error: any) => {
        toast.error('Failed to fetch data')
        console.error(error)
      })
    }
    fetchData()
  }, [])


  const handleOpen = (feedback?: Feedback) => {
    setSelectedFeedback(feedback ?? null)
    setFormData(feedback ?? {})
    setIsOpen(true)
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedFeedback(null)
    setFormData({})
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSave = async () => {
    try {
      if (selectedFeedback) {
        // Exclude id, user and timestamps from update data to match backend schema
        const { id, user, created_at, updated_at, ...updateData } = formData
        const updated = await feedbackApi.update(selectedFeedback.id, updateData)
        setFeedbacks(prev => prev.map(f => f.id === updated.id ? { ...f, ...updated } : f))
        toast.success('Feedback updated')
      } else {
        // If create is supported
        // const created = await feedbackApi.create(formData as Omit<Feedback, 'id' | 'created_at' | 'updated_at'>)
        // setFeedbacks(prev => [...prev, created])
        // toast.success('Feedback created')
      }
      handleClose()
    } catch (error: any) {
      toast.error('Failed to save feedback')
      console.error(error)
    }
  }

  const handleDelete = async () => {
    if (!selectedFeedback) return
    if (confirm('Delete this feedback?')) {
      await withLoading(async () => {
        await feedbackApi.delete(selectedFeedback.id)
        setFeedbacks(prev => prev.filter(f => f.id !== selectedFeedback.id))
        toast.success('Feedback deleted')
        handleClose()
      }).catch((error: any) => {
        toast.error('Failed to delete feedback')
        console.error(error)
      })
    }
  }

  const formatDate = (dateString: string) => new Date(dateString).toLocaleDateString('ru-RU', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

  const FooterButtons = () => (
    <>
      <Button onClick={handleSave}>Save</Button>
      {selectedFeedback && (
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
          <Label htmlFor="answer">Answer</Label>
          <Input id="answer" name="answer" value={formData.answer ?? ''} onChange={handleInputChange} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="text">Text</Label>
          <Input id="text" name="text" value={formData.text ?? ''} onChange={handleInputChange} />
        </div>
      </div>
    </>
  )

  // Add columns
  const columns: ColumnDef<Feedback>[] = [
    {
      id: "select",
      header: ({ table }) => <Checkbox checked={table.getIsAllPageRowsSelected() || (table.getIsSomePageRowsSelected() && "indeterminate")} onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)} />,
      cell: ({ row }) => <Checkbox checked={row.getIsSelected()} onCheckedChange={(value) => row.toggleSelected(!!value)} />,
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
      header: "Пользователь",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="font-medium">{row.original.user?.last_name ?? ''} {row.original.user?.first_name ?? ''}</div>
          <div className="text-sm text-muted-foreground">@{row.original.user?.username}</div>
        </div>
      ),
    },
    {
      accessorKey: "feedback",
      header: "Отзыв",
      cell: ({ row }) => (
        <div className="space-y-1 max-w-md">
          <div className="text-sm font-medium line-clamp-2">{row.original.answer}</div>
          {row.original.text && <div className="text-xs text-muted-foreground line-clamp-1">{row.original.text}</div>}
        </div>
      ),
    },
    {
      accessorKey: "date",
      header: "Дата",
      cell: ({ row }) => <div className="text-sm">{formatDate(row.original.created_at)}</div>,
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <div className="flex items-center space-x-2">
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
            title="Отзывы пользователей"
            description="Анализ и управление отзывами пользователей"
          />

          <DataTable data={feedbacks} columns={columns} loading={loading} loadingMessage="Загрузка отзывов..." />
        </div>
      </SidebarInset>

      {isMobile ? (
        <Drawer open={isOpen} onOpenChange={setIsOpen}>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>Edit Feedback</DrawerTitle>
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
              <SheetTitle>Edit Feedback</SheetTitle>
              <SheetDescription>
                Edit feedback information and status for user reviews.
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