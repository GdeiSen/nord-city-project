import { Button } from "@/components/ui/button"
import { IconUserPlus } from "@tabler/icons-react"

interface PageHeaderProps {
  title: string
  description: string
  buttonText?: string
  onButtonClick?: () => void
  buttonIcon?: React.ReactNode
}

export function PageHeader({ 
  title, 
  description, 
  buttonText, 
  onButtonClick, 
  buttonIcon 
}: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
        <p className="text-muted-foreground">{description}</p>
      </div>
      {buttonText && onButtonClick && (
        <Button onClick={onButtonClick} size="default" className="whitespace-nowrap shrink-0">
          {buttonIcon}
          {buttonText}
        </Button>
      )}
    </div>
  )
}
