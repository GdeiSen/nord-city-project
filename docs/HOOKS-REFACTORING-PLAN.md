# План рефакторинга: вынос логики в хуки

> План рефакторинга веб-приложения (Next.js): вынос повторяющейся логики со страниц в переиспользуемые хуки и утилиты.

> **Правило:** При рефакторинге страниц одного типа обновляются **все** страницы этой группы. Нельзя рефакторить только часть — это создаёт разорванность кодовой базы.

---

## Анализ на дату создания

- **Dashboard** исключён из плана — планируется значительная переработка.
- **List-страницы** (users, service-tickets, feedbacks) уже используют общие хуки — дублирования минимум.
- **formatDate** дублируется в **8 файлах** — приоритетная утилита.

---

## Группа 6: Общие утилиты (подготовка)

> Выполнить первой — снижает дублирование перед основным рефакторингом.

### 6.1 `useRouteId`

**Проблема:** Один и тот же код разбора id из params повторяется на всех edit и detail страницах.

**Файлы с дублированием:**
- `app/users/edit/[[...id]]/page.tsx` — `params?.id?.[0]`, `parseInt`, `isEdit`
- `app/service-tickets/edit/[[...id]]/page.tsx`
- `app/feedbacks/edit/[[...id]]/page.tsx`
- `app/spaces/edit/[[...id]]/page.tsx`
- `app/users/[id]/page.tsx` — `params?.id`, `Number(params?.id)`
- `app/service-tickets/[id]/page.tsx`
- `app/feedbacks/[id]/page.tsx`
- `app/spaces/[id]/page.tsx` — `params?.id` (objectId)
- `app/spaces/[id]/edit/[[...spaceId]]/page.tsx` — `objectId` + `spaceId`
- `app/spaces/[id]/[spaceId]/page.tsx` — `objectId` + `spaceId`

**Хук:**
```ts
// hooks/use-route-id.ts
function useRouteId(options?: {
  paramKey?: string
  parseMode?: 'number' | 'string'
}): { id: number | null; isEdit: boolean }
// Для catch-all [[...id]]: idParam = params?.id?.[0]
// Для обычного [id]: id = Number(params?.id)
```

**Примечание:** `spaces/[id]/edit` и `spaces/[id]/[spaceId]` имеют два параметра (objectId, spaceId). Варианты: отдельный `useSpaceRouteIds` или параметр `paramKeys: ['id', 'spaceId']`.

---

### 6.2 `formatDate` → lib

**Проблема:** Функция форматирования даты дублируется в 8 файлах с небольшими вариациями (locale, с/без времени).

**Файлы:**
- `app/users/page.tsx`
- `app/service-tickets/page.tsx`
- `app/feedbacks/page.tsx`
- `app/users/[id]/page.tsx`
- `app/service-tickets/[id]/page.tsx`
- `app/feedbacks/[id]/page.tsx`
- `app/spaces/page.tsx`
- `app/spaces/[id]/[spaceId]/page.tsx`

**Решение:**
```ts
// lib/date-utils.ts
export function formatDate(
  dateString: string,
  options?: { includeTime?: boolean; locale?: string }
): string
```

**Варьируемые опции:** `includeTime` (по умолчанию true для detail, false для кратких форматов), `locale: 'ru-RU'`.

---

### 6.3 `formatApiError` → lib

**Проблема:** Функция `formatError` в `login/page.tsx` (строки 21–44) разбирает API-ошибки. Может пригодиться и на других страницах (toast, alert).

**Решение:**
```ts
// lib/format-api-error.ts
export function formatApiError(err: unknown): { title: string; details: string }
```

---

## Группа 3: Edit/Create-страницы (формы)

> Рефакторить **все 5** страниц одновременно.

### Хук: `useEntityForm<T>`

**Инкапсулирует:**
- Разбор id из params (`useRouteId` или встроенный)
- `useLoading(true)`
- `formData`, `setFormData`, `saving`, `setSaving`
- `useEffect` загрузки начальных данных (getById для edit, default values для create)
- `handleInputChange(name, value)`, `handleSelectChange(name, value)`
- `handleSave` — подготовка payload, create/update, toast, redirect
- `handleDelete` — только для edit, delete API, toast, redirect

**Страницы (5 шт.):**

| Файл | Сущность | Особенности |
|------|----------|-------------|
| `app/users/edit/[[...id]]/page.tsx` | User | DataPicker для object, role как number |
| `app/service-tickets/edit/[[...id]]/page.tsx` | ServiceTicket | DataPicker user + object, allowedFields, priority parse |
| `app/feedbacks/edit/[[...id]]/page.tsx` | Feedback | Только edit (create не поддерживается) |
| `app/spaces/edit/[[...id]]/page.tsx` | RentalObject | PhotoLinksEditor, status, photos |
| `app/spaces/[id]/edit/[[...spaceId]]/page.tsx` | RentalSpace | objectId из route, spaceId опционален |

**Опции хука:**
```ts
interface UseEntityFormOptions<T> {
  entityId: number | null
  isEdit: boolean
  fetchInitial: () => Promise<T | Partial<T>>
  defaultValues: Partial<T>
  preparePayload: (data: Partial<T>) => Record<string, unknown>
  onCreate: (payload: any) => Promise<{ id: number }>
  onUpdate: (id: number, payload: any) => Promise<void>
  onDelete?: (id: number) => Promise<void>
  createRedirect: (created: { id: number }) => string
  updateRedirect: (id: number) => string
  deleteRedirect: string
  errorMessages: { load: string; save: string; delete: string }
}
```

**Примечание:** Из-за различий в preparePayload и DataPicker, хук может быть параметризован колбэками. Либо базовый `useEntityForm` + страницы передают свои `preparePayload`, `fetchInitial` и т.д.

---

## Группа 2: Detail-страницы

> Рефакторить **все 5** страниц одновременно.

### Хук: `useEntityDetail<T>`

**Инкапсулирует:**
- id из params
- `useLoading(true)`
- `data`, `setData` (useState)
- `useEffect` с fetcher (getById + связанные сущности при необходимости)
- Обработка ошибок, toast, redirect при неуспехе

**Страницы (5 шт.):**

| Файл | Сущность | Особенности |
|------|----------|-------------|
| `app/users/[id]/page.tsx` | User | getById + rentalObjectApi.getAll для object |
| `app/service-tickets/[id]/page.tsx` | ServiceTicket | getById + userApi.getAll для user |
| `app/feedbacks/[id]/page.tsx` | Feedback | getById + userApi.getAll для user |
| `app/spaces/[id]/page.tsx` | RentalObject + Spaces | **Гибрид:** object + список spaces, DataTable, spaceStats. Требует `useRentalObjectSpaces` |
| `app/spaces/[id]/[spaceId]/page.tsx` | RentalSpace | Два id (objectId, spaceId), getById space + object (name) |

**Опции хука:**
```ts
interface UseEntityDetailOptions<T> {
  id: number | null
  fetcher: () => Promise<T>
  notFoundRedirect?: string
  errorMessage?: string
}
```

**Для spaces/[id]:** Логика отличается (object + spaces + stats). Отдельный хук `useRentalObjectSpaces(objectId)`.
**Для spaces/[id]/[spaceId]:** Два id. Либо `useEntityDetail` с `id: spaceId` и доп. `objectId`, либо `useSpaceDetail(objectId, spaceId)`.

---

## Группа 4: Auth

> Рефакторить **обе** части одновременно.

### 4.1 `useOtpAuth`

**Файл:** `app/login/page.tsx`

**Инкапсулирует:**
- `step`, `setStep` ('enter_id' | 'enter_otp')
- `identifier`, `setIdentifier`
- `resolvedUserId`, `setResolvedUserId`
- `otpCode`, `setOtpCode`
- `errorInfo`, `setErrorInfo`
- `loading`, `setLoading`
- `handleRequestOtp` — authApi.requestOtp, переход на step enter_otp
- `handleVerifyOtp` — authApi.verifyOtp, setToken, setUser, onSuccess (router.push)
- `handleOtpChange` — сброс ошибки, авто-verify при 6 символах

**Опции:**
```ts
interface UseOtpAuthOptions {
  onSuccess?: () => void  // обычно router.push('/')
}
```

**Возвращает:** `{ step, identifier, setIdentifier, loading, errorInfo, setErrorInfo, handleRequestOtp, handleVerifyOtp, handleOtpChange }`

---

### 4.2 `useAuthCheck`

**Файл:** `components/auth-guard.tsx`

**Инкапсулирует:**
- `checked`, `authorized` (useState)
- useEffect: pathname, PUBLIC_ROUTES, isAuthenticated, getToken, authApi.validateToken, logout
- Логика: публичные роуты → authorized; нет токена → redirect; валидация токена → authorized или redirect

**Опции:**
```ts
interface UseAuthCheckOptions {
  pathname: string
  publicRoutes?: string[]
}
```

**Возвращает:** `{ checked, authorized }`

**Результат:** AuthGuard становится тонкой обёрткой: вызывает `useAuthCheck(pathname)`, рендерит спиннер или children.

---

## Группа 5: Spaces-страницы

> Рефакторить **все связанные** страницы одновременно.

### 5.1 `useBusinessCentersWithStats`

**Файл:** `app/spaces/page.tsx`

**Инкапсулирует:**
- `businessCenters`, `setBusinessCenters`
- `loading`, `setLoading`
- `fetchData` — rentalObjectApi.getAll, rentalSpaceApi.getAll, агрегация (parseFloorNumber, stats)
- `parseFloorNumber`, `getOccupancyRate`, `getStatusVariant`
- `formatDate` (после 6.2 — из lib)

**Возвращает:** `{ businessCenters, loading, refetch }`

---

### 5.2 `useRentalObjectSpaces`

**Файл:** `app/spaces/[id]/page.tsx`

**Инкапсулирует:**
- `objectId` из params
- `rentalObject`, `spaces` (useState)
- `loading`, `withLoading`
- `fetchSpaces` — getById object, getByObjectId spaces
- `spaceStats` (useMemo): total, free, occupied, totalArea, maxFloor
- `getSpaceStatusBadge` (SPACE_STATUS_LABELS, SPACE_STATUS_VARIANTS)

**Возвращает:** `{ rentalObject, spaces, spaceStats, loading, refetch, getSpaceStatusBadge }`

---

### 5.3 Space detail (`spaces/[id]/[spaceId]`)

**Файл:** `app/spaces/[id]/[spaceId]/page.tsx`

Можно использовать обобщённый `useEntityDetail` с fetcher, возвращающим space + objectName. Либо `useSpaceDetail(objectId, spaceId)` — специализированный хук для помещения.

---

## Группа 1: List-страницы (таблица)

**Статус:** Уже используют `useServerPaginatedData`, `useFilterPickerData`, `useCanEdit`. Дополнительный рефакторинг не требуется.

**Оставшееся дублирование:**
- `formatDate` — убрать через группу 6.2
- `getRoleBadge` (users), аналогичные badge-хелперы — можно оставить в компонентах или вынести в `lib/table-configs` при появлении дублирования

---

## Чеклист выполнения

```
✅ Группа 6.1 — useRouteId (+ useSpaceRouteIds)
✅ Группа 6.2 — formatDate → lib/date-utils.ts (обновлено 8 файлов)
✅ Группа 6.3 — formatApiError → lib/format-api-error.ts

✅ Группа 3 — useRouteId/useSpaceRouteIds на всех 5 edit страницах; useEntityForm (Feedback)
□ Группа 2 — useEntityDetail + useRentalObjectSpaces (все 5 detail страниц)
✅ Группа 4 — useOtpAuth + useAuthCheck (login + auth-guard)
□ Группа 5 — useBusinessCentersWithStats + useRentalObjectSpaces + space detail (spaces/*)
```

---

## Рекомендуемый порядок

1. **Группа 6** — утилиты (useRouteId, formatDate, formatApiError)
2. **Группа 3** — Edit-страницы (максимальное дублирование)
3. **Группа 2** — Detail-страницы
4. **Группа 4** — Auth
5. **Группа 5** — Spaces

---

## Опционально (низкий приоритет)

### `useSearchFilter` для DataPicker

**Файл:** `components/data-picker.tsx`

**Инкапсулирует:** searchTerm, filteredData по searchableFields. Имеет смысл только при повторном использовании этой логики в других компонентах.
