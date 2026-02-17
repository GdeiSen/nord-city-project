"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { useLoading } from "@/hooks/ui/use-loading"

export interface UseEntityFormOptions<T> {
  entityId: number | null
  isEdit: boolean
  fetchInitial: () => Promise<Partial<T> | void>
  defaultValues: Partial<T>
  preparePayload: (data: Partial<T>) => Record<string, unknown>
  onCreate: (payload: Record<string, unknown>) => Promise<{ id: number }>
  onUpdate: (id: number, payload: Record<string, unknown>) => Promise<void>
  onDelete?: (id: number) => Promise<void>
  createRedirect: (created: { id: number }) => string
  updateRedirect: (id: number) => string
  deleteRedirect: string
  errorMessages: { load: string; save: string; delete: string }
  successMessages?: { save: string; create: string; delete: string }
  onLoadErrorRedirect?: () => string
}

export interface UseEntityFormReturn<T> {
  loading: boolean
  formData: Partial<T>
  setFormData: React.Dispatch<React.SetStateAction<Partial<T>>>
  saving: boolean
  handleInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  handleSelectChange: (name: string, value: string | number) => void
  handleSave: () => Promise<void>
  handleDelete: () => Promise<void>
}

export function useEntityForm<T>(options: UseEntityFormOptions<T>): UseEntityFormReturn<T> {
  const {
    entityId,
    isEdit,
    fetchInitial,
    defaultValues,
    preparePayload,
    onCreate,
    onUpdate,
    onDelete,
    createRedirect,
    updateRedirect,
    deleteRedirect,
    errorMessages,
    successMessages,
    onLoadErrorRedirect,
  } = options

  const router = useRouter()
  const { loading, withLoading } = useLoading(true)
  const [formData, setFormData] = useState<Partial<T>>(defaultValues)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const load = async () => {
      const data = await fetchInitial()
      if (data !== undefined) {
        setFormData(data)
      }
    }
    withLoading(load).catch(() => {
      toast.error(errorMessages.load)
      const redirect = onLoadErrorRedirect?.() ?? (isEdit && entityId ? updateRedirect(entityId) : deleteRedirect)
      router.push(redirect)
    })
  }, [entityId, isEdit]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }, [])

  const handleSelectChange = useCallback((name: string, value: string | number) => {
    setFormData((prev) => ({ ...prev, [name]: value }))
  }, [])

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      const payload = preparePayload(formData)
      if (isEdit && entityId != null) {
        await onUpdate(entityId, payload)
        toast.success(successMessages?.save ?? "Сохранено")
        router.push(updateRedirect(entityId))
      } else {
        const created = await onCreate(payload)
        toast.success(successMessages?.create ?? "Создано")
        router.push(createRedirect(created))
      }
    } catch {
      toast.error(errorMessages.save)
    } finally {
      setSaving(false)
    }
  }, [
    formData,
    isEdit,
    entityId,
    preparePayload,
    onCreate,
    onUpdate,
    createRedirect,
    updateRedirect,
    deleteRedirect,
    errorMessages.save,
    router,
  ])

  const handleDelete = useCallback(async () => {
    if (!isEdit || entityId == null || !onDelete) return
    try {
      await onDelete(entityId)
      toast.success(successMessages?.delete ?? "Удалено")
      router.push(deleteRedirect)
    } catch {
      toast.error(errorMessages.delete)
    }
  }, [isEdit, entityId, onDelete, deleteRedirect, errorMessages.delete, router])

  return {
    loading,
    formData,
    setFormData,
    saving,
    handleInputChange,
    handleSelectChange,
    handleSave,
    handleDelete,
  }
}
