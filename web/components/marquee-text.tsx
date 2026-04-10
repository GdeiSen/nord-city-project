"use client"

import * as React from "react"

import { useMarqueeAnimationsDisabled } from "@/hooks/ui/use-marquee-animations"
import { cn } from "@/lib/utils"

export interface MarqueeTextProps {
  text?: string | null
  className?: string
  textClassName?: string
  title?: string
  maxWidthPx?: number
}

export function MarqueeText({
  text,
  className,
  textClassName,
  title,
  maxWidthPx = 360,
}: MarqueeTextProps) {
  const value = text == null ? "" : String(text)
  const [animationsDisabled] = useMarqueeAnimationsDisabled()
  const containerRef = React.useRef<HTMLDivElement>(null)
  const contentRef = React.useRef<HTMLSpanElement>(null)
  const [contentWidth, setContentWidth] = React.useState(0)
  const [overflowOffset, setOverflowOffset] = React.useState(0)

  React.useEffect(() => {
    if (!containerRef.current || !contentRef.current) {
      return
    }

    const measure = () => {
      const containerWidth = containerRef.current?.clientWidth ?? 0
      const nextContentWidth = contentRef.current?.scrollWidth ?? 0
      const nextOffset = Math.max(0, Math.ceil(nextContentWidth - containerWidth))
      setContentWidth(nextContentWidth)
      setOverflowOffset(nextOffset)
    }

    measure()

    if (typeof ResizeObserver === "undefined") {
      return
    }

    const observer = new ResizeObserver(() => {
      measure()
    })
    observer.observe(containerRef.current)
    observer.observe(contentRef.current)

    return () => {
      observer.disconnect()
    }
  }, [value])

  const hasOverflow = overflowOffset > 8
  const shouldAnimate = hasOverflow && !animationsDisabled
  const animationDuration = `${Math.min(18, Math.max(7, overflowOffset / 26))}s`
  const clampedWidth = contentWidth > 0 ? Math.min(contentWidth, maxWidthPx) : null
  const animationStyle = shouldAnimate
    ? ({
        ["--marquee-shift" as string]: `-${overflowOffset}px`,
        ["--marquee-duration" as string]: animationDuration,
      } as React.CSSProperties)
    : undefined

  return (
    <div
      ref={containerRef}
      className={cn("relative min-w-0 max-w-full overflow-hidden", className)}
      title={title ?? value}
      style={
        clampedWidth
          ? ({
              width: `${clampedWidth}px`,
              maxWidth: "100%",
            } as React.CSSProperties)
          : undefined
      }
    >
      {shouldAnimate && (
        <>
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 left-0 z-10 w-6 animate-marquee-left-fade bg-gradient-to-r from-background via-background/90 to-transparent"
            style={animationStyle}
          />
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 right-0 z-10 w-6 animate-marquee-right-fade bg-gradient-to-l from-background via-background/90 to-transparent"
            style={animationStyle}
          />
        </>
      )}

      <span
        ref={contentRef}
        className={cn(
          "block min-w-0 whitespace-nowrap",
          shouldAnimate
            ? "max-w-max animate-marquee-bounce pr-8 will-change-transform"
            : "max-w-full truncate",
          textClassName
        )}
        style={animationStyle}
      >
        {value}
      </span>
    </div>
  )
}
