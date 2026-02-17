import { getToken } from "@/lib/auth"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8003/api/v1"

interface PaginatedResponse<T> {
  items: T[]
  total: number
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== "undefined" ? getToken() : null
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) || {}),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  })

  if (res.status === 204) {
    return undefined as T
  }

  const text = await res.text()
  let data: any
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    throw new Error(res.statusText || "Request failed")
  }

  if (!res.ok) {
    const detail = data?.detail
    let msg: string
    if (typeof detail === "string") {
      msg = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      msg = detail
        .map((e: { loc?: unknown[]; msg?: string }) => {
          const loc = Array.isArray(e.loc) ? e.loc.join(" ") : ""
          return (loc ? `${loc}: ` : "") + (e.msg || "")
        })
        .join("; ")
    } else {
      msg = (detail as { msg?: string })?.msg || res.statusText || "Request failed"
    }
    const err = new Error(msg) as Error & { status?: number; details?: unknown }
    err.status = res.status
    err.details = detail
    throw err
  }

  return data as T
}

async function fetchAllPages<T>(
  path: string,
  pageSize = 500
): Promise<T[]> {
  const all: T[] = []
  let page = 1
  let total = 0
  do {
    const sep = path.includes("?") ? "&" : "?"
    const res = await apiFetch<PaginatedResponse<T>>(
      `${path}${sep}page=${page}&page_size=${pageSize}`
    )
    const items = res?.items ?? []
    total = res?.total ?? 0
    all.push(...items)
    if (all.length >= total) break
    page++
  } while (all.length < total)
  return all
}

import type { FilterItem } from "@/types/filters"

export type { FilterItem as ServerFilterItem } from "@/types/filters"

export interface GetPaginatedParams {
  page?: number
  pageSize?: number
  search?: string
  sort?: string
  searchColumns?: string[]
  filters?: FilterItem[]
}

function createCrudApi<T extends { id: number }>(
  basePath: string
) {
  return {
    async getAll(): Promise<T[]> {
      return fetchAllPages<T>(`${basePath}/`)
    },

    async getPaginated(params: GetPaginatedParams = {}): Promise<PaginatedResponse<T>> {
      const { page = 1, pageSize = 10, search, sort, searchColumns, filters } = params
      const q = new URLSearchParams()
      q.set("page", String(page))
      q.set("page_size", String(pageSize))
      if (search) q.set("search", search)
      if (sort) q.set("sort", sort)
      if (searchColumns?.length) q.set("search_columns", searchColumns.join(","))
      if (filters?.length) q.set("filters", JSON.stringify(filters))
      const res = await apiFetch<PaginatedResponse<T>>(`${basePath}/?${q}`)
      return { items: res?.items ?? [], total: res?.total ?? 0 }
    },

    async getById(id: number): Promise<T> {
      return apiFetch<T>(`${basePath}/${id}`)
    },

    async create(data: Partial<T>): Promise<T> {
      return apiFetch<T>(`${basePath}/`, {
        method: "POST",
        body: JSON.stringify(data),
      })
    },

    async update(id: number, data: Partial<T>): Promise<void> {
      await apiFetch<void>(`${basePath}/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      })
    },

    async delete(id: number): Promise<void> {
      await apiFetch<void>(`${basePath}/${id}`, {
        method: "DELETE",
      })
    },
  }
}

// Auth API (OTP flow + token validation)
export const authApi = {
  /**
   * Request OTP code. Provide either userId (Telegram ID) or username (e.g. "johndoe" or "@johndoe").
   * Returns user_id for use in verifyOtp when lookup was by username.
   */
  async requestOtp(params: { userId?: number; username?: string }): Promise<{
    success: boolean
    message?: string
    user_id?: number
  }> {
    const body: Record<string, unknown> = {}
    if (params.userId != null) body.user_id = params.userId
    if (params.username != null && params.username.trim()) body.username = params.username.trim()
    return apiFetch("/auth/request-otp", {
      method: "POST",
      body: JSON.stringify(body),
    })
  },

  async verifyOtp(
    userId: number,
    code: string
  ): Promise<{ success: boolean; access_token?: string; user?: any }> {
    return apiFetch("/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, code }),
    })
  },

  async validateToken(token: string): Promise<{ valid: boolean }> {
    const res = await fetch(`${API_BASE}/auth/validate`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json().catch(() => ({}))
    return { valid: !!data?.valid }
  },
}

// Media upload (multipart/form-data)
export const mediaApi = {
  async upload(file: File): Promise<{ path: string; url: string }> {
    const token = typeof window !== "undefined" ? getToken() : null
    const headers: Record<string, string> = {}
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch(`${API_BASE}/media/upload`, {
      method: "POST",
      headers,
      body: formData,
    })

    const text = await res.text()
    let data: any
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      throw new Error(res.statusText || "Upload failed")
    }

    if (!res.ok) {
      const msg = typeof data?.detail === "string" ? data.detail : data?.detail?.msg ?? res.statusText
      throw new Error(msg)
    }
    return data
  },
}

/** Params for CSV export - matches current table view (filters, sort, columns) */
export interface GetExportParams {
  page?: number
  pageSize?: number
  search?: string
  sort?: string
  searchColumns?: string[]
  filters?: FilterItem[]
  columns: string[]
  limit: number
}

function createExportApi(basePath: string) {
  return {
    async getExport(params: GetExportParams): Promise<Blob> {
      const { columns, limit, search, sort, searchColumns, filters } = params
      const q = new URLSearchParams()
      q.set("columns", columns.join(","))
      q.set("limit", String(limit))
      if (search) q.set("search", search)
      if (sort) q.set("sort", sort)
      if (searchColumns?.length) q.set("search_columns", searchColumns.join(","))
      if (filters?.length) q.set("filters", JSON.stringify(filters))
      const token = typeof window !== "undefined" ? getToken() : null
      const headers: Record<string, string> = {}
      if (token) headers["Authorization"] = `Bearer ${token}`
      const res = await fetch(`${API_BASE}${basePath}/export?${q}`, { headers })
      if (!res.ok) {
        const text = await res.text()
        let detail = res.statusText
        try {
          const data = JSON.parse(text)
          detail = typeof data?.detail === "string" ? data.detail : data?.detail?.msg ?? detail
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      return res.blob()
    },
  }
}

// Resource APIs
const userBase = createCrudApi<any>("/users")
export const userApi = {
  ...userBase,
  ...createExportApi("/users"),
}
const serviceTicketBase = createCrudApi<any>("/service-tickets")
export const serviceTicketApi = {
  ...serviceTicketBase,
  ...createExportApi("/service-tickets"),
}

// Audit log (read-only)
export const auditLogApi = {
  async getByEntity(entityType: string, entityId: number): Promise<any[]> {
    const params = new URLSearchParams({
      entity_type: entityType,
      entity_id: String(entityId),
    })
    return apiFetch<any[]>(`/audit-log/?${params}`)
  },

  async getPaginated(params: GetPaginatedParams = {}): Promise<PaginatedResponse<any>> {
    const { page = 1, pageSize = 10, search, sort, searchColumns, filters } = params
    const q = new URLSearchParams()
    q.set("page", String(page))
    q.set("page_size", String(pageSize))
    if (search) q.set("search", search)
    if (sort) q.set("sort", sort)
    if (searchColumns?.length) q.set("search_columns", searchColumns.join(","))
    if (filters?.length) q.set("filters", JSON.stringify(filters))
    const res = await apiFetch<PaginatedResponse<any>>(`/audit-log/list?${q}`)
    return { items: res?.items ?? [], total: res?.total ?? 0 }
  },
}
const feedbackBase = createCrudApi<any>("/feedbacks")
export const feedbackApi = {
  ...feedbackBase,
  ...createExportApi("/feedbacks"),
}
export const rentalObjectApi = createCrudApi<any>("/rental-objects")

// Rental spaces: base CRUD + getByObjectId (GET /rental-spaces/rental-objects/{object_id})
const rentalSpaceBase = createCrudApi<any>("/rental-spaces")
export const rentalSpaceApi = {
  ...rentalSpaceBase,
  async getByObjectId(objectId: number): Promise<any[]> {
    const res = await apiFetch<any[]>(
      `/rental-spaces/rental-objects/${objectId}`
    )
    return Array.isArray(res) ? res : []
  },
}
