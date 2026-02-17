"use client"

import { useState, useEffect } from "react"
import { userApi, rentalObjectApi } from "@/lib/api"

export interface FilterPickerUser {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  email?: string
}

export interface FilterPickerObject {
  id: number
  name: string
}

export interface FilterPickerData {
  users?: FilterPickerUser[]
  objects?: FilterPickerObject[]
}

export interface UseFilterPickerDataOptions {
  /** Fetch users for filter picker (e.g. user_id, created_by) */
  users?: boolean
  /** Fetch rental objects for filter picker (e.g. object_id) */
  objects?: boolean
}

/**
 * Fetches and caches users/objects for DataTable filter pickers.
 * Avoids duplicate API calls across pages - each page requests only what it needs.
 */
export function useFilterPickerData(options: UseFilterPickerDataOptions = {}): FilterPickerData {
  const { users: needUsers = false, objects: needObjects = false } = options
  const [users, setUsers] = useState<FilterPickerUser[]>([])
  const [objects, setObjects] = useState<FilterPickerObject[]>([])

  useEffect(() => {
    if (needUsers) {
      userApi.getAll().then(setUsers).catch(console.error)
    }
  }, [needUsers])

  useEffect(() => {
    if (needObjects) {
      rentalObjectApi.getAll().then(setObjects).catch(console.error)
    }
  }, [needObjects])

  return {
    users: needUsers ? users : undefined,
    objects: needObjects ? objects : undefined,
  }
}
