"use client"

import * as React from "react"

import { EntityPicker, type EntityPickerOption } from "@/components/entity-picker"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import type { FilterPickerUser } from "@/hooks/data/use-filter-picker-data"

export interface NotificationDeliverySelection {
  roleIds: number[]
  userIds: number[]
}

interface NotificationDeliverySheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  value: NotificationDeliverySelection
  users: FilterPickerUser[]
  roleOptions: EntityPickerOption[]
  onApply: (value: NotificationDeliverySelection) => void
}

function toPickerValue(values: number[]): string {
  return values.map(String).join(",")
}

function fromPickerValue(value: string): number[] {
  return Array.from(
    new Set(
      String(value || "")
        .split(",")
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isFinite(item))
    )
  )
}

function getUserLabel(user: FilterPickerUser): string {
  const name = `${user.last_name ?? ""} ${user.first_name ?? ""}`.trim()
  const username = user.username ? `@${user.username}` : ""
  return `${name} ${username}`.trim() || `#${user.id}`
}

export function NotificationDeliverySheet({
  open,
  onOpenChange,
  value,
  users,
  roleOptions,
  onApply,
}: NotificationDeliverySheetProps) {
  const [draft, setDraft] = React.useState<NotificationDeliverySelection>(value)

  React.useEffect(() => {
    if (open) {
      setDraft(value)
    }
  }, [open, value])

  const availableUserOptions = React.useMemo(() => {
    const selectedRoleIds = new Set(draft.roleIds)
    const selectedUserIds = new Set(draft.userIds)
    const visibleUsers = selectedRoleIds.size
      ? users.filter((user) => (user.role != null && selectedRoleIds.has(user.role)) || selectedUserIds.has(user.id))
      : users

    return visibleUsers
      .map((user) => ({
        value: String(user.id),
        label: getUserLabel(user),
      }))
      .sort((left, right) => left.label.localeCompare(right.label, "ru"))
  }, [draft.roleIds, draft.userIds, users])

  const applySelection = () => {
    onApply(draft)
    onOpenChange(false)
  }

  const resetSelection = () => {
    setDraft({ roleIds: [], userIds: [] })
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:!max-w-md">
        <SheetHeader>
          <SheetTitle>Настройка отправки</SheetTitle>
          <SheetDescription>
            Выберите роли, конкретных пользователей или их комбинацию. Получатели будут объединены без дублей.
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 px-4">
          <div className="space-y-5 pb-4">
            <div className="space-y-2">
              <div className="space-y-1">
                <p className="text-sm font-medium">Роли пользователей</p>
                <p className="text-sm text-muted-foreground">
                  Список ролей использует тот же набор значений, что и фильтры таблицы пользователей.
                </p>
              </div>
              <EntityPicker
                multiple
                options={roleOptions}
                value={toPickerValue(draft.roleIds)}
                onChange={(nextValue) =>
                  setDraft((current) => ({
                    ...current,
                    roleIds: fromPickerValue(nextValue),
                  }))
                }
                placeholder="Выберите роли"
              />
            </div>

            <Separator />

            <div className="space-y-2">
              <div className="space-y-1">
                <p className="text-sm font-medium">Конкретные пользователи</p>
                <p className="text-sm text-muted-foreground">
                  Список пользователей фильтруется по выбранным ролям и сохраняет уже отмеченных получателей.
                </p>
              </div>
              <EntityPicker
                multiple
                options={availableUserOptions}
                value={toPickerValue(draft.userIds)}
                onChange={(nextValue) =>
                  setDraft((current) => ({
                    ...current,
                    userIds: fromPickerValue(nextValue),
                  }))
                }
                placeholder="Выберите пользователей"
                emptyMessage="Нет пользователей для выбранных ролей"
              />
            </div>
          </div>
        </ScrollArea>

        <SheetFooter>
          <Button type="button" variant="ghost" onClick={resetSelection}>
            Сбросить
          </Button>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
          <Button type="button" onClick={applySelection}>
            Применить
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
