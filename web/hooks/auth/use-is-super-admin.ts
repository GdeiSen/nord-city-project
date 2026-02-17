import { getUser } from "@/lib/auth"
import { USER_ROLES } from "@/types"

/**
 * Returns true if the current user is Super Admin (full privileges).
 */
export function useIsSuperAdmin(): boolean {
  const user = getUser()
  if (!user?.role) return false
  return user.role === USER_ROLES.SUPER_ADMIN
}
