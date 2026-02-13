"use client"

import { useEffect } from "react"

/**
 * Компонент для подавления предупреждений React о неизвестных пропсах от recharts
 * 
 * Эти предупреждения возникают из-за того, что recharts передает внутренние пропсы,
 * которые React 19 считает DOM атрибутами. Это известная проблема совместимости.
 */
export function SuppressConsoleWarnings() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") {
      return
    }

    const originalError = console.error
    const originalWarn = console.warn

    // Список предупреждений, которые нужно игнорировать
    const suppressedMessages = [
      "React does not recognize the `allowEscapeViewBox` prop",
      "React does not recognize the `animationDuration` prop",
      "React does not recognize the `animationEasing` prop",
      "React does not recognize the `axisId` prop",
      "React does not recognize the `contentStyle` prop",
      "React does not recognize the `filterNull` prop",
      "React does not recognize the `isAnimationActive` prop",
      "React does not recognize the `itemSorter` prop",
      "React does not recognize the `itemStyle` prop",
      "React does not recognize the `labelStyle` prop",
      "React does not recognize the `reverseDirection` prop",
      "React does not recognize the `useTranslate3d` prop",
      "React does not recognize the `wrapperStyle` prop",
      "React does not recognize the `accessibilityLayer` prop",
      "Received `true` for a non-boolean attribute `cursor`",
      "spell it as lowercase",
    ]

    const filterMessage = (message: string): boolean => {
      return suppressedMessages.some((suppressed) =>
        message.includes(suppressed)
      )
    }

    console.error = (...args: any[]) => {
      const message = args[0]?.toString() || ""
      if (filterMessage(message)) {
        return
      }
      originalError.apply(console, args)
    }

    console.warn = (...args: any[]) => {
      const message = args[0]?.toString() || ""
      if (filterMessage(message)) {
        return
      }
      originalWarn.apply(console, args)
    }

    return () => {
      console.error = originalError
      console.warn = originalWarn
    }
  }, [])

  return null
}
