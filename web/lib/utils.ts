import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Truncates string to maxLength and adds "..." if truncated */
export function truncate(text: string | undefined | null, maxLength: number): string {
  if (text == null || text === "") return ""
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + "..."
}
