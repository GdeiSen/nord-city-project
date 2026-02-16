"use client"

import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg"
  className?: string
}

export function LoadingSpinner({ size = "md", className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "size-4",
    md: "size-6",
    lg: "size-8"
  }

  return <Spinner className={cn(sizeClasses[size], className)} />
}

interface LoadingPageProps {
  message?: string
  showSpinner?: boolean
  className?: string
}

export function LoadingPage({ 
  message = "Loading...", 
  showSpinner = true,
  className 
}: LoadingPageProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center h-screen space-y-4", className)}>
      {showSpinner && <LoadingSpinner size="lg" />}
      <p className="text-muted-foreground text-lg">{message}</p>
    </div>
  )
}
