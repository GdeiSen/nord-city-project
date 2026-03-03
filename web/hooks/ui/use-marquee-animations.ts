"use client"

import * as React from "react"

const STORAGE_KEY = "nord-city:disable-marquee-animations"
const EVENT_NAME = "nord-city:marquee-animations-change"
const subscribers = new Set<() => void>()

let listenersRegistered = false

function readDisabledState(): boolean {
  if (typeof window === "undefined") {
    return false
  }

  return window.localStorage.getItem(STORAGE_KEY) === "1"
}

function applyDisabledState(disabled: boolean) {
  if (typeof document === "undefined") {
    return
  }

  document.documentElement.dataset.marqueeAnimations = disabled ? "disabled" : "enabled"
}

function emitChange() {
  for (const callback of subscribers) {
    callback()
  }
}

function syncAndEmit() {
  const nextValue = readDisabledState()
  applyDisabledState(nextValue)
  emitChange()
}

function ensureListeners() {
  if (listenersRegistered || typeof window === "undefined") {
    return
  }

  window.addEventListener(EVENT_NAME, syncAndEmit)
  window.addEventListener("storage", syncAndEmit)
  listenersRegistered = true
}

export function setMarqueeAnimationsDisabled(disabled: boolean) {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(STORAGE_KEY, disabled ? "1" : "0")
  applyDisabledState(disabled)
  window.dispatchEvent(new Event(EVENT_NAME))
}

export function useMarqueeAnimationsDisabled() {
  const disabled = React.useSyncExternalStore(
    (callback) => {
      ensureListeners()
      subscribers.add(callback)
      return () => {
        subscribers.delete(callback)
      }
    },
    () => {
      const nextValue = readDisabledState()
      applyDisabledState(nextValue)
      return nextValue
    },
    () => false
  )

  const update = React.useCallback((nextValue: boolean) => {
    setMarqueeAnimationsDisabled(nextValue)
  }, [])

  return [disabled, update] as const
}
