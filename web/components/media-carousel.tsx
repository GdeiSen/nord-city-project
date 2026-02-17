"use client"

import * as React from "react"
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel"
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

function isImageUrl(url: string): boolean {
  return /\.(jpe?g|png|gif|webp)(\?|$)/i.test(url)
}

export interface MediaCarouselProps {
  items: string[]
  className?: string
  /** Placeholder when empty */
  emptyMessage?: string
}

export function MediaCarousel({
  items,
  className,
  emptyMessage = "Фотографии не добавлены",
}: MediaCarouselProps) {
  const [selectedUrl, setSelectedUrl] = React.useState<string | null>(null)

  if (!items?.length) {
    return (
      <div
        className={cn(
          "flex h-24 w-full items-center justify-center rounded-lg border border-dashed bg-muted/50",
          className
        )}
      >
        <span className="text-sm text-muted-foreground">{emptyMessage}</span>
      </div>
    )
  }

  return (
    <>
      <Carousel
        opts={{ align: "start", loop: true }}
        className={cn("w-full", className)}
      >
        <CarouselContent className="-ml-2 sm:-ml-3">
          {items.map((url, i) => (
            <CarouselItem
              key={`${i}-${url}`}
              className="basis-1/2 pl-2 sm:basis-1/3 sm:pl-3 md:basis-1/4 lg:basis-1/5"
            >
              <button
                type="button"
                onClick={() => setSelectedUrl(url)}
                className="relative h-36 w-full cursor-pointer overflow-hidden rounded-lg bg-muted text-left sm:h-40 focus:outline-none focus:ring-0"
              >
                {isImageUrl(url) ? (
                  <img
                    src={url}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <video
                    src={url}
                    className="h-full w-full object-cover"
                    muted
                    playsInline
                    preload="metadata"
                  />
                )}
              </button>
            </CarouselItem>
          ))}
        </CarouselContent>
        <CarouselPrevious className="left-2" />
        <CarouselNext className="right-2" />
      </Carousel>

      <Dialog open={!!selectedUrl} onOpenChange={(open) => !open && setSelectedUrl(null)}>
        <DialogContent
          className="max-w-[95vw] max-h-[95vh] w-auto p-0 border-none bg-transparent overflow-hidden [&>button]:bg-black/70 [&>button]:text-white [&>button]:hover:bg-black/90"
          showCloseButton={true}
        >
          <DialogTitle className="sr-only">Просмотр фотографии</DialogTitle>
          {selectedUrl && (
            isImageUrl(selectedUrl) ? (
              <img
                src={selectedUrl}
                alt=""
                className="max-h-[90vh] w-auto max-w-full object-contain"
              />
            ) : (
              <video
                src={selectedUrl}
                className="max-h-[90vh] w-auto max-w-full"
                controls
                autoPlay
              />
            )
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
