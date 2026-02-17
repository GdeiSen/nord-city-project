/**
 * Hooks barrel export.
 * Structure: auth | data | data-table | forms | routing | ui
 * Use @/hooks for barrel or @/hooks/{category}/{name} for granular imports.
 */

// Auth
export { useAuthCheck } from "./auth/use-auth-check"
export { useCanEdit } from "./auth/use-can-edit"
export { useIsSuperAdmin } from "./auth/use-is-super-admin"
export { useOtpAuth } from "./auth/use-otp-auth"

// Data
export {
  useFilterPickerData,
  type FilterPickerData,
  type FilterPickerUser,
  type FilterPickerObject,
  type UseFilterPickerDataOptions,
} from "./data/use-filter-picker-data"
export { useServerPaginatedData } from "./data/use-server-paginated-data"

// Data table
export { useDataTableFiltersAndSorts } from "./data-table/use-data-table-filters-and-sorts"
export { useServerParamsSync } from "./data-table/use-server-params-sync"

// Forms
export { useEntityForm } from "./forms/use-entity-form"

// Routing
export { useRouteId, useSpaceRouteIds } from "./routing/use-route-id"

// UI
export { useDebounce } from "./ui/use-debounce"
export { useDeleteDialog } from "./ui/use-delete-dialog"
export { useLoading } from "./ui/use-loading"
export { useIsMobile } from "./ui/use-mobile"
