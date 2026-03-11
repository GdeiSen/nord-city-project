import { Button } from "@/components/ui/button"

interface PageHeaderProps {
  title: string
  description: string
  buttonText?: string
  onButtonClick?: () => void
  buttonIcon?: React.ReactNode
  actions?: React.ReactNode
}

export function PageHeader({ 
  title, 
  description, 
  buttonText, 
  onButtonClick, 
  buttonIcon,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight">{title}</h2>
        <p className="text-muted-foreground">{description}</p>
      </div>
      {actions ? actions : buttonText && onButtonClick && (
        <Button onClick={onButtonClick} size="default" className="whitespace-nowrap shrink-0">
          {buttonIcon}
          {buttonText}
        </Button>
      )}
    </div>
  )
}
