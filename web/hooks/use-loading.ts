"use client"

import { useState, useCallback } from "react"

interface UseLoadingReturn {
  loading: boolean
  setLoading: (loading: boolean) => void
  withLoading: <T>(asyncFn: () => Promise<T>) => Promise<T | undefined>
}

export function useLoading(initialState: boolean = false): UseLoadingReturn {
  const [loading, setLoading] = useState(initialState)

  const withLoading = useCallback(async <T>(asyncFn: () => Promise<T>): Promise<T | undefined> => {
    try {
      setLoading(true)
      const result = await asyncFn()
      return result
    } catch (error) {
      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    loading,
    setLoading,
    withLoading
  }
}
