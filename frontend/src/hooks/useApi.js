import { useState, useEffect } from 'react'

export function useApi(url, deps = []) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    if (!url) {
      setLoading(false)
      return
    }

    const controller = new AbortController()
    let active = true

    setLoading(true)
    setError(null)
    fetch(url, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(d  => {
        if (!active) return
        setData(d)
        setLoading(false)
      })
      .catch(e => {
        if (!active || e.name === 'AbortError') return
        setError(e.message)
        setLoading(false)
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [url, ...deps])

  return { data, loading, error }
}

export function buildUrl(base, params = {}) {
  const u = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined) u.append(k, v)
  })
  const qs = u.toString()
  return qs ? `${base}?${qs}` : base
}
