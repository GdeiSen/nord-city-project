import { getUser } from "@/lib/auth"

/**
 * Returns true if the current user is Super Admin (full privileges).
 */
export function useIsSuperAdmin(): boolean {
  const user = getUser()
  return !!user?.is_super_admin
}
