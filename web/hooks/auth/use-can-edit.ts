import { getUser } from "@/lib/auth"
import { USER_ROLES } from "@/types"

/**
 * Returns true if the current user is Admin or Super Admin and can edit entities.
 */
export function useCanEdit(): boolean {
  const user = getUser()
  if (!user?.role) return false
  return user.role === USER_ROLES.ADMIN || user.role === USER_ROLES.SUPER_ADMIN
}
