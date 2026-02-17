"use client"

import { useParams } from "next/navigation"

export interface UseRouteIdOptions {
  /** Key for catch-all params (e.g. 'id' for [[...id]], 'spaceId' for [[...spaceId]]) */
  paramKey?: string
  /** How to parse: 'number' for numeric IDs, 'string' for object IDs */
  parseMode?: "number" | "string"
  /** For routes with multiple params (e.g. spaces/[id]/[spaceId]) */
  paramKeys?: [string, string]
}

export interface UseRouteIdResult {
  id: number | string | null
  isEdit: boolean
}

export interface UseSpaceRouteIdsResult {
  objectId: number | null
  spaceId: number | null
  isEdit: boolean
}

/**
 * Extract ID from route params for edit/create and detail pages.
 * Supports both catch-all [[...id]] and regular [id] segments.
 */
export function useRouteId(options?: UseRouteIdOptions): UseRouteIdResult {
  const { paramKey = "id", parseMode = "number" } = options ?? {}
  const params = useParams<Record<string, string | string[]>>()

  // Catch-all: params.id = ["123"] or ["edit", "123"]
  const raw = paramKey ? (params?.[paramKey] as string[] | string | undefined) : undefined
  const idParam = Array.isArray(raw) ? raw[0] : raw
  const id =
    parseMode === "number"
      ? idParam != null && idParam !== ""
        ? parseInt(idParam, 10)
        : null
      : idParam ?? null
  const isEdit =
    id != null && (parseMode === "string" ? !!id : typeof id === "number" && !Number.isNaN(id))

  return { id: id as number | string | null, isEdit }
}

/**
 * For spaces/[id]/edit/[[...spaceId]] and spaces/[id]/[spaceId]:
 * objectId from [id], spaceId from [spaceId] or [[...spaceId]].
 */
export function useSpaceRouteIds(): UseSpaceRouteIdsResult {
  const params = useParams<{ id?: string; spaceId?: string | string[] }>()
  const objectIdParam = params?.id
  const objectId =
    objectIdParam != null && objectIdParam !== ""
      ? parseInt(String(objectIdParam), 10)
      : null
  const spaceIdRaw = params?.spaceId
  const spaceIdParam = Array.isArray(spaceIdRaw) ? spaceIdRaw[0] : spaceIdRaw
  const spaceId =
    spaceIdParam != null && spaceIdParam !== ""
      ? parseInt(String(spaceIdParam), 10)
      : null
  const isEdit =
    objectId != null &&
    !Number.isNaN(objectId) &&
    spaceId != null &&
    !Number.isNaN(spaceId)

  return { objectId, spaceId, isEdit }
}
