"use client"

import { useState, useCallback } from "react"

export interface UseDeleteDialogReturn<T> {
  open: boolean
  pendingRow: T | null
  requestDelete: (row: T | null) => void
  /** Call after performing delete. Clears pending row and closes dialog. */
  confirmDelete: () => void
  cancel: () => void
  setOpen: (open: boolean) => void
}

/**
 * Manages delete confirmation dialog state: pending row and open/close.
 */
export function useDeleteDialog<T>(): UseDeleteDialogReturn<T> {
  const [open, setOpen] = useState(false)
  const [pendingRow, setPendingRow] = useState<T | null>(null)

  const requestDelete = useCallback((row: T | null) => {
    setPendingRow(row)
    setOpen(true)
  }, [])

  const confirmDelete = useCallback(() => {
    setOpen(false)
    setPendingRow(null)
  }, [])

  const cancel = useCallback(() => {
    setOpen(false)
    setPendingRow(null)
  }, [])

  return {
    open,
    pendingRow,
    requestDelete,
    confirmDelete,
    cancel,
    setOpen,
  }
}
