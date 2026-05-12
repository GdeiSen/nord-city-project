import { getUser } from "@/lib/auth"

/**
 * Returns true if the current user is Admin or Super Admin and can edit entities.
 */
export function useCanEdit(): boolean {
  const user = getUser()
  return !!user?.is_super_admin || !!user?.permissions?.includes("users.manage")
}
