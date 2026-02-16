"use client"

import { ReactNode } from "react"
import { LoadingPage } from "./loading-spinner"

interface LoadingWrapperProps {
  loading: boolean
  children: ReactNode
  loadingMessage?: string
  showSpinner?: boolean
  className?: string
}

export function LoadingWrapper({ 
  loading, 
  children, 
  loadingMessage = "Loading...",
  showSpinner = true,
  className 
}: LoadingWrapperProps) {
  if (loading) {
    return <LoadingPage message={loadingMessage} showSpinner={showSpinner} className={className} />
  }

  return <>{children}</>
}
