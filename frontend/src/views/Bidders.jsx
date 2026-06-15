import { useEffect, useState, useCallback, useMemo } from 'react'
import { Cpu } from 'lucide-react'

const fmtDate = (d) => (d ? d.slice(0, 10) : '-')

const fmtMoneyCompact = (n, currency = 'USD') => {
  if (!n || Number(n) === 0) return '-'
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(Number(n))
  } catch {
    return `${currency || ''} ${Number(n).toLocaleString()}`
  }
}

const fmtMoneyFull = (n, currency = 'USD') => {
  if (!n || Number(n) === 0) return '-'
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(Number(n))
  } catch {
    return `${currency || ''} ${Number(n).toLocaleString()}`
  }
}

const FLAG_CODES = {
  China: 'cn', India: 'in', Turkey: 'tr', Spain: 'es', Bangladesh: 'bd',
  Poland: 'pl', Senegal: 'sn', Nigeria: 'ng', Pakistan: 'pk', Ethiopia: 'et',
  Brazil: 'br', 'United States': 'us', 'United Kingdom': 'gb', France: 'fr',
  Germany: 'de', Indonesia: 'id', Philippines: 'ph', Thailand: 'th',
  Malaysia: 'my', Egypt: 'eg', Morocco: 'ma', Kenya: 'ke', Ghana: 'gh',
  Uganda: 'ug', Rwanda: 'rw', Tanzania: 'tz', Malawi: 'mw', Zambia: 'zm',
  Mozambique: 'mz', Angola: 'ao', Botswana: 'bw', Benin: 'bj',
  Cameroon: 'cm', Somalia: 'so', 'Somalia, Federal Republic of': 'so', Guinea: 'gn', Gambia: 'gm',
  'Sierra Leone': 'sl', 'South Africa': 'za', 'Viet Nam': 'vn',
  'Central African Republic': 'cf',
}

const flagUrl = (country = '') => {
  const code = FLAG_CODES[country] || country.slice(0, 2).toLowerCase()
  return `https://flagcdn.com/20x15/${code}.png`
}

function Badge({ type }) {
  const colors = {
    IFB: { bg: 'rgba(53,208,127,0.12)', color: 'var(--ifb)' },
    REOI: { bg: 'rgba(124,111,255,0.12)', color: 'var(--reoi)' },
    'Contract Award': { bg: 'rgba(167,243,194,0.16)', color: 'var(--accent2)' },
    Award: { bg: 'rgba(167,243,194,0.16)', color: 'var(--accent2)' },
  }
  const s = colors[type] || { bg: 'rgba(255,255,255,0.06)', color: 'var(--text2)' }
  return (
    <span style={{
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.color}33`,
      borderRadius: 999,
      padding: '2px 8px',
      fontSize: 11,
      fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {type || '-'}
    </span>
  )
}

function RolePill({ role, won }) {
  const color = won ? 'var(--accent)' : 'var(--accent2)'
  return (
    <span style={{
      background: won ? 'rgba(53,208,127,0.14)' : 'rgba(167,243,194,0.12)',
      color,
      border: `1px solid ${color}44`,
      borderRadius: 999,
      padding: '3px 8px',
      fontSize: 11,
      fontWeight: 700,
      whiteSpace: 'nowrap',
    }}>
      {won ? 'Won' : (role || 'Bid')}
    </span>
  )
}

function StatPill({ label, value, accent }) {
  return (
    <div style={{
      background: 'var(--surface2)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      padding: '10px 16px',
      minWidth: 110,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: accent || 'var(--text)' }}>{value}</div>
    </div>
  )
}

function MetaField({ label, value }) {
  if (!value) return null
  return (
    <div>
      <div style={{ color: 'var(--text3)', fontSize: 11 }}>{label}</div>
      <div style={{ color: 'var(--text)', wordBreak: 'break-word' }}>{value}</div>
    </div>
  )
}

function BidderExportButton({ filters, total }) {
  const [showFields, setShowFields] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportType, setExportType] = useState('excel')
  const [selectedFields, setSelectedFields] = useState([
    'name', 'country', 'category', 'bid_count', 'won_count', 'total_bid_amount', 'primary_currency', 'last_bid_date',
  ])

  const availableFields = [
    ['name', 'Bidder Name'],
    ['country', 'Country of Origin'],
    ['category', 'Category'],
    ['bid_count', 'Total Bids'],
    ['won_count', 'Won Bids'],
    ['total_bid_amount', 'Total Bid Amount'],
    ['primary_currency', 'Currency'],
    ['last_bid_date', 'Last Bid Date'],
    ['latest_bid_title', 'Latest Bid'],
    ['contact_name', 'Contact Name'],
    ['contact_email', 'Contact Email'],
    ['contact_phone', 'Contact Phone'],
    ['contact_org', 'Organisation'],
  ]

  const toggleField = (field) => {
    setSelectedFields(current => current.includes(field) ? current.filter(item => item !== field) : [...current, field])
  }

  const runExport = async () => {
    if (!selectedFields.length) return
    setExporting(true)
    try {
      const params = new URLSearchParams()
      if (filters.search) params.set('search', filters.search)
      if (filters.country) params.set('country', filters.country)
      if (filters.won_only) params.set('won_only', 'true')
      params.set('fields', selectedFields.join(','))
      const endpoint = exportType === 'csv' ? '/api/bidders/export/csv' : '/api/bidders/export'
      const res = await fetch(`${endpoint}?${params.toString()}`)
      if (!res.ok) throw new Error('Export failed')
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      const filename = match ? match[1] : (exportType === 'csv' ? 'bidders.csv' : 'bidders.xlsx')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      setShowFields(false)
    } catch {
      window.alert('Failed to export bidders.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setShowFields(current => !current)}
        disabled={total === 0 || exporting}
        style={{
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          color: 'var(--text)',
          borderRadius: 10,
          padding: '8px 14px',
          fontSize: 13,
          fontWeight: 600,
          opacity: total === 0 ? 0.5 : 1,
        }}
      >
        {exporting ? 'Exporting...' : 'Custom Export'}
      </button>

      {showFields && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          width: 320,
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          boxShadow: 'var(--shadow)',
          padding: 16,
          zIndex: 20,
        }}>
          <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 10 }}>Choose export columns</div>
          <div style={{ display: 'grid', gap: 8, maxHeight: 240, overflowY: 'auto' }}>
            {availableFields.map(([key, label]) => (
              <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text2)', fontSize: 13 }}>
                <input type="checkbox" checked={selectedFields.includes(key)} onChange={() => toggleField(key)} />
                <span>{label}</span>
              </label>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 14, marginBottom: 14 }}>
            <button onClick={() => setExportType('excel')} style={{
              background: exportType === 'excel' ? 'var(--accent)' : 'var(--surface2)',
              color: exportType === 'excel' ? 'var(--surface)' : 'var(--text2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 12,
            }}>Excel</button>
            <button onClick={() => setExportType('csv')} style={{
              background: exportType === 'csv' ? 'var(--accent)' : 'var(--surface2)',
              color: exportType === 'csv' ? 'var(--surface)' : 'var(--text2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 12,
            }}>CSV</button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button onClick={() => setShowFields(false)} style={{
              background: 'transparent',
              color: 'var(--text3)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 12,
            }}>Cancel</button>
            <button onClick={runExport} disabled={!selectedFields.length || exporting} style={{
              background: 'var(--accent)',
              color: 'var(--surface)',
              border: 'none',
              borderRadius: 8,
              padding: '6px 12px',
              fontSize: 12,
              fontWeight: 700,
            }}>Export</button>
          </div>
        </div>
      )}
    </div>
  )
}

function BidderDetail({ bidder, onClose, onSaved, onDeleted }) {
  const [notices, setNotices] = useState([])
  const [loadingNotices, setLoadingNotices] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ ...bidder })
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    setForm({ ...bidder })
    setLoadingNotices(true)
    fetch(`/api/bidders/${bidder.id}/notices`)
      .then(r => r.json())
      .then(setNotices)
      .catch(() => setNotices([]))
      .finally(() => setLoadingNotices(false))
  }, [bidder.id, bidder])

  const save = async () => {
    setSaving(true)
    try {
      const res = await fetch(`/api/bidders/${bidder.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) {
        onSaved()
        setEditing(false)
      }
    } finally {
      setSaving(false)
    }
  }

  const removeBidder = async () => {
    if (!window.confirm(`Delete bidder "${bidder.name}" and all linked bid records?`)) return
    setDeleting(true)
    try {
      const res = await fetch(`/api/bidders/${bidder.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Delete failed')
      onDeleted?.()
    } catch (error) {
      window.alert('Failed to delete bidder.')
    } finally {
      setDeleting(false)
    }
  }

  const won = notices.filter(n => n.won)
  const totalAmount = notices.reduce((sum, n) => sum + (Number(n.bid_amount) || 0), 0)
  const primaryCurrency = bidder.primary_currency || notices.find(n => n.bid_currency)?.bid_currency || 'USD'

  return (
    <aside style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: 'min(620px, 96vw)',
      height: '100vh',
      background: 'var(--surface)',
      borderLeft: '1px solid var(--border)',
      overflowY: 'auto',
      zIndex: 999,
      boxShadow: 'var(--shadow)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: '22px 24px 18px',
        borderBottom: '1px solid var(--border)',
        background: 'linear-gradient(180deg, color-mix(in srgb, var(--accent) 14%, var(--surface)) 0%, var(--surface) 100%)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
              BIDDER #{bidder.id}
            </div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: 'var(--text)', wordBreak: 'break-word' }}>
              {bidder.name}
            </h2>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {bidder.is_tech && (
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                  fontSize: 10, fontFamily: 'var(--font-mono)',
                  background: '#0d2b1e', color: '#00d4aa',
                  padding: '2px 6px', borderRadius: 4,
                  fontWeight: 600,
                }}>
                  <Cpu size={10} /> TECH
                </span>
              )}
              {bidder.country && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text2)', fontSize: 13 }}>
                  <img
                    src={flagUrl(bidder.country)}
                    alt=""
                    style={{ width: 20, height: 15, borderRadius: 2, objectFit: 'cover' }}
                    onError={e => { e.target.style.display = 'none' }}
                  />
                  {bidder.country}
                </span>
              )}
              {bidder.category && <RolePill role={bidder.category} />}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              color: 'var(--text2)',
              borderRadius: 10,
              padding: '7px 12px',
              fontSize: 12,
            }}
          >
            Close
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <StatPill label="Total Bids" value={bidder.bid_count ?? notices.length} />
          <StatPill label="Won" value={bidder.won_count ?? won.length} accent="var(--accent)" />
          <StatPill label="Total Amount" value={fmtMoneyCompact(bidder.total_bid_amount ?? totalAmount, primaryCurrency)} accent="var(--accent2)" />
        </div>
      </div>

      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        {!editing ? (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 16px', fontSize: 13 }}>
              <MetaField label="Country of Origin" value={bidder.country} />
              <MetaField label="Category" value={bidder.category} />
              <MetaField label="Contact Name" value={bidder.contact_name} />
              <MetaField label="Email" value={bidder.contact_email} />
              <MetaField label="Phone" value={bidder.contact_phone} />
              <MetaField label="Organisation" value={bidder.contact_org} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <button
                onClick={() => setEditing(true)}
                style={{
                  background: 'var(--surface2)',
                  border: '1px solid var(--border)',
                  color: 'var(--text2)',
                  borderRadius: 8,
                  padding: '6px 14px',
                  fontSize: 12,
                }}
              >
                Edit Details
              </button>
              <button
                onClick={removeBidder}
                disabled={deleting}
                style={{
                  background: 'rgba(239,68,68,0.12)',
                  border: '1px solid var(--danger)',
                  color: 'var(--danger)',
                  borderRadius: 8,
                  padding: '6px 14px',
                  fontSize: 12,
                  fontWeight: 700,
                  opacity: deleting ? 0.7 : 1,
                }}
              >
                {deleting ? 'Deleting...' : 'Delete Bidder'}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {[
                ['name', 'Name'],
                ['category', 'Category'],
                ['country', 'Country of Origin'],
                ['contact_name', 'Contact Name'],
                ['contact_email', 'Email'],
                ['contact_phone', 'Phone'],
                ['contact_org', 'Organisation'],
              ].map(([key, label]) => (
                <div key={key}>
                  <label style={{ display: 'block', fontSize: 11, color: 'var(--text3)', marginBottom: 3 }}>
                    {label}
                  </label>
                  <input
                    value={form[key] || ''}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '7px 10px',
                      background: 'var(--bg)',
                      border: '1px solid var(--border2)',
                      borderRadius: 8,
                      color: 'var(--text)',
                      fontSize: 13,
                    }}
                  />
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button
                onClick={() => setEditing(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  color: 'var(--text2)',
                  borderRadius: 8,
                  padding: '6px 14px',
                  fontSize: 12,
                }}
              >
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving}
                style={{
                  background: 'var(--accent)',
                  border: 'none',
                  color: 'var(--surface)',
                  borderRadius: 8,
                  padding: '6px 16px',
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px 24px' }}>
        <div style={{
          fontSize: 12,
          color: 'var(--text3)',
          fontFamily: 'var(--font-mono)',
          marginBottom: 12,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          Bids and awarded contracts ({notices.length})
        </div>
        {loadingNotices ? (
          <div style={{ color: 'var(--text3)', fontSize: 13 }}>Loading...</div>
        ) : notices.length === 0 ? (
          <div style={{ color: 'var(--text3)', fontSize: 13 }}>
            No linked notices yet. Use "Import All Awards" to populate.
          </div>
        ) : notices.map(n => (
          <div
            key={`${n.id}-${n.role || 'notice'}`}
            style={{
              background: 'var(--surface2)',
              border: '1px solid var(--border)',
              borderRadius: 14,
              padding: '14px 16px',
              marginBottom: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text)', wordBreak: 'break-word', lineHeight: 1.45 }}>
                  {n.title || '(no title)'}
                </div>
                <div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 2 }}>
                  {n.project_name || n.project_id || ''}
                </div>
              </div>
              <RolePill role={n.role} won={n.won} />
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 14px', fontSize: 12, color: 'var(--text2)' }}>
              <Badge type={n.notice_type} />
              {n.borrower_country && <span>Country: {n.borrower_country}</span>}
              {n.bid_amount ? (
                <span style={{ color: 'var(--accent2)', fontWeight: 700 }}>
                  Bid Amount: {fmtMoneyFull(n.bid_amount, n.bid_currency || 'USD')}
                </span>
              ) : null}
              {n.award_date && <span>Date: {fmtDate(n.award_date)}</span>}
            </div>

            {n.url && (
              <a
                href={n.url}
                target="_blank"
                rel="noreferrer"
                style={{ display: 'inline-block', marginTop: 8, fontSize: 11, color: 'var(--accent2)' }}
              >
                View on World Bank
              </a>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}

export default function Bidders() {
  const [data, setData] = useState([])
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importingCountry, setImportingCountry] = useState(false)
  const [importingMissingCountry, setImportingMissingCountry] = useState(false)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [wonOnly, setWonOnly] = useState(false)
  const [techOnly, setTechOnly] = useState(false)
  const [selected, setSelected] = useState(null)
  const [importStatus, setImportStatus] = useState(null)
  const [finishingImport, setFinishingImport] = useState(false)
  const [countryOptions, setCountryOptions] = useState([])

  const fetchBidders = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page, page_size: 25 })
      if (search) params.set('search', search)
      if (country) params.set('country', country)
      if (wonOnly) params.set('won_only', 'true')
      const res = await fetch(`/api/bidders?${params}`)
      const json = await res.json()
      if (Array.isArray(json)) {
        setData(json)
        setTotal(json.length)
        setTotalPages(1)
      } else {
        const mapped = (json.data || []).map(r => ({ ...r, is_tech: r.is_tech ?? false }))
        setData(mapped)
        setTotal(json.total ?? 0)
        setTotalPages(json.total_pages ?? 1)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [page, search, country, wonOnly])

  const filteredData = useMemo(() => {
    if (!techOnly) return data
    return data.filter(b => b.is_tech)
  }, [data, techOnly])

  useEffect(() => { fetchBidders() }, [fetchBidders])
  useEffect(() => { setPage(1) }, [search, country, wonOnly, techOnly])

  useEffect(() => {
    fetch('/api/bidders/countries')
      .then(res => res.ok ? res.json() : [])
      .then(json => setCountryOptions(Array.isArray(json) ? json : []))
      .catch(() => setCountryOptions([]))
  }, [])

  const fetchImportStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/bidders/import_status')
      if (!res.ok) return
      const json = await res.json()
      setImportStatus(json)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => { fetchImportStatus() }, [fetchImportStatus])

  const importAll = async () => {
    setImporting(true)
    try {
      await fetch('/api/bidders/import_awards_all', { method: 'POST' })
      alert('Batch import started in background. Refresh shortly to see the updated bidder details.')
    } finally {
      setImporting(false)
    }
  }

  const importSelectedCountry = async (missingOnly = false) => {
    if (!country.trim()) {
      window.alert('Enter or select a country first.')
      return
    }

    const encodedCountry = encodeURIComponent(country.trim())
    const endpoint = missingOnly
      ? `/api/bidders/import_missing_by_country?country=${encodedCountry}`
      : `/api/bidders/import_by_country?country=${encodedCountry}`

    if (missingOnly) setImportingMissingCountry(true)
    else setImportingCountry(true)

    try {
      const res = await fetch(endpoint, { method: 'POST' })
      if (!res.ok) throw new Error('Country import failed')
      const data = await res.json()
      if (missingOnly) {
        await fetchBidders()
        await fetchImportStatus()
        window.alert(`Missing bidder import finished for ${country}. Processed ${data.processed ?? 0} notices.`)
      } else {
        window.alert(`Country bidder import started for ${country}. Refresh shortly to see updated bidder details.`)
      }
    } catch {
      window.alert(`Failed to import bidders for ${country}.`)
    } finally {
      if (missingOnly) setImportingMissingCountry(false)
      else setImportingCountry(false)
    }
  }

  const importMissing = async () => {
    setFinishingImport(true)
    try {
      const res = await fetch('/api/bidders/import_missing', { method: 'POST' })
      if (!res.ok) throw new Error('Import missing failed')
      await fetchBidders()
      await fetchImportStatus()
      window.alert('Missing bidder imports finished.')
    } catch {
      window.alert('Failed to finish missing bidder imports.')
    } finally {
      setFinishingImport(false)
    }
  }

  const inputStyle = {
    background: 'var(--surface2)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    borderRadius: 10,
    padding: '8px 12px',
    fontSize: 13,
    outline: 'none',
    fontFamily: 'inherit',
  }

  const btnStyle = (active, danger) => ({
    background: danger ? 'rgba(239,68,68,0.1)' : active ? 'var(--accent)' : 'var(--surface2)',
    border: `1px solid ${danger ? 'var(--danger)' : active ? 'var(--accent)' : 'var(--border)'}`,
    color: danger ? 'var(--danger)' : active ? 'var(--surface)' : 'var(--text2)',
    borderRadius: 10,
    padding: '8px 14px',
    fontSize: 13,
    fontWeight: active ? 700 : 500,
    fontFamily: 'inherit',
  })

  const thStyle = {
    textAlign: 'left',
    padding: '12px 14px',
    fontSize: 11,
    color: 'var(--text3)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    borderBottom: '1px solid var(--border)',
    fontFamily: 'var(--font-mono)',
    whiteSpace: 'nowrap',
    background: 'var(--surface)',
  }

  const tdStyle = (i) => ({
    padding: '12px 14px',
    borderBottom: '1px solid var(--border)',
    background: i % 2 === 0 ? 'color-mix(in srgb, var(--surface2) 38%, transparent)' : 'transparent',
    verticalAlign: 'middle',
    fontSize: 13,
  })

  return (
    <div style={{ padding: 24 }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 20,
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div>
          <h2 style={{ margin: 0, fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 24, color: 'var(--text)' }}>
            Bidders and Companies
          </h2>
          <p style={{ margin: '4px 0 0', color: 'var(--text3)', fontSize: 13 }}>
            {total.toLocaleString()} companies with country of origin, category, bid totals, and awarded-contract history
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <button onClick={importAll} disabled={importing} style={btnStyle(false, false)}>
            {importing ? 'Importing...' : 'Import All Awards'}
          </button>
          <BidderExportButton filters={{ search, country, won_only: wonOnly }} total={total} />
        </div>
      </div>

      {importStatus && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
          marginBottom: 18,
          padding: '14px 16px',
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
        }}>
          <div>
            <div style={{ fontWeight: 700, color: 'var(--text)' }}>
              Bidder import coverage: {importStatus.linked_award_notices} / {importStatus.total_award_notices} award notices
            </div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4 }}>
              Missing notices: {importStatus.missing_award_notices}
              {importStatus.missing_award_notices > 0 && importStatus.missing_samples?.length ? ` | Sample: ${importStatus.missing_samples.map(item => item.id).join(', ')}` : ''}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={fetchImportStatus} style={btnStyle(false, false)}>Refresh Status</button>
            <button
              onClick={importMissing}
              disabled={finishingImport || !importStatus.missing_award_notices}
              style={btnStyle(false, false)}
            >
              {finishingImport ? 'Finishing...' : 'Import Missing'}
            </button>
          </div>
        </div>
      )}

      <div style={{
        display: 'flex',
        gap: 10,
        marginBottom: 18,
        flexWrap: 'wrap',
        alignItems: 'center',
        padding: 14,
        borderRadius: 14,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
      }}>
        <input
          style={{ ...inputStyle, flex: '1 1 220px' }}
          placeholder="Search company, organisation, or contact..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          style={{ ...inputStyle, minWidth: 160, flex: '0 1 180px' }}
          value={country}
          onChange={e => setCountry(e.target.value)}
        >
          <option value="">All bidder countries</option>
          {countryOptions.map(option => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
        <button onClick={() => setWonOnly(w => !w)} style={btnStyle(wonOnly)}>
          {wonOnly ? 'Won only active' : 'Won only'}
        </button>
        <button onClick={() => setTechOnly(t => !t)} style={{
          ...btnStyle(techOnly),
          background: techOnly ? '#0d2b1e' : 'transparent',
          borderColor: techOnly ? '#00d4aa' : 'var(--border)',
          color: techOnly ? '#00d4aa' : 'var(--text2)',
        }}>
          <Cpu size={13} style={{ marginRight: 4 }} />{techOnly ? 'Tech only' : 'Tech'}
        </button>
        <button
          onClick={() => { setSearch(''); setCountry(''); setWonOnly(false); setTechOnly(false); setPage(1) }}
          style={{ ...btnStyle(false), color: 'var(--text3)' }}
        >
          Reset
        </button>
      </div>

      <div style={{
        display: 'flex',
        gap: 10,
        marginBottom: 18,
        flexWrap: 'wrap',
        alignItems: 'center',
        padding: 14,
        borderRadius: 14,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
      }}>
        <div style={{ flex: '1 1 260px' }}>
          <div style={{ color: 'var(--text)', fontWeight: 700, marginBottom: 4 }}>Country-Specific Bidder Import</div>
          <div style={{ color: 'var(--text3)', fontSize: 12 }}>
            Use the current country filter to import bidders only for that country.
          </div>
        </div>
        <button
          onClick={() => importSelectedCountry(false)}
          disabled={importingCountry || !country.trim()}
          style={btnStyle(false, false)}
        >
          {importingCountry ? 'Starting...' : 'Import This Country'}
        </button>
        <button
          onClick={() => importSelectedCountry(true)}
          disabled={importingMissingCountry || !country.trim()}
          style={btnStyle(false, false)}
        >
          {importingMissingCountry ? 'Finishing...' : 'Import Missing for This Country'}
        </button>
      </div>

      <div style={{
        border: '1px solid var(--border)',
        borderRadius: 16,
        overflow: 'hidden',
        background: 'var(--surface)',
        boxShadow: 'var(--shadow)',
      }}>
        <div style={{ width: '100%', overflowX: 'auto' }}>
        <table style={{ width: '100%', minWidth: 1060, borderCollapse: 'collapse', tableLayout: 'fixed' }}>
          <thead>
            <tr>
              {['Tech', 'Company / Bidder', 'Country of Origin', 'Category', 'Bids', 'Won', 'Total Bid Amount', 'Last Bid', ''].map(h => (
                <th key={h} style={thStyle}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} style={{ ...tdStyle(0), textAlign: 'center', padding: '32px', color: 'var(--text3)' }}>
                  Loading...
                </td>
              </tr>
            ) : filteredData.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ ...tdStyle(0), textAlign: 'center', padding: '32px', color: 'var(--text3)' }}>
                  No bidders found. {!search && !country && 'Try importing all awards to rebuild bidder details from your award notices.'}
                </td>
              </tr>
            ) : filteredData.map((b, i) => (
              <tr key={b.id} style={{ cursor: 'pointer' }} onClick={() => setSelected(b)}>
                <td style={{ ...tdStyle(i), textAlign: 'center' }}>
                  {b.is_tech ? (
                    <span style={{
                      fontSize: 10, fontFamily: 'var(--font-mono)',
                      background: '#0d2b1e', color: '#00d4aa',
                      padding: '2px 6px', borderRadius: 4,
                      fontWeight: 600,
                    }} title="Tech bidder">
                      <Cpu size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />TECH
                    </span>
                  ) : (
                    <span style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>--</span>
                  )}
                </td>
                <td style={tdStyle(i)}>
                  <div style={{
                    fontWeight: 700,
                    color: 'var(--text)',
                    lineHeight: 1.45,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }} title={b.name}>
                    {b.name}
                  </div>
                  {b.contact_org && b.contact_org !== b.name && (
                    <div style={{
                      color: 'var(--text3)',
                      fontSize: 11,
                      display: '-webkit-box',
                      WebkitLineClamp: 1,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {b.contact_org}
                    </div>
                  )}
                </td>
                <td style={tdStyle(i)}>
                  {b.country ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <img
                        src={flagUrl(b.country)}
                        alt=""
                        style={{ width: 20, height: 15, borderRadius: 2, objectFit: 'cover' }}
                        onError={e => { e.target.style.display = 'none' }}
                      />
                      <span>{b.country}</span>
                    </div>
                  ) : <span style={{ color: 'var(--text3)' }}>-</span>}
                </td>
                <td style={{ ...tdStyle(i), color: 'var(--text2)' }}>
                  {b.category || <span style={{ color: 'var(--text3)' }}>-</span>}
                </td>
                <td style={{ ...tdStyle(i), textAlign: 'center', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text)' }}>
                  {b.bid_count ?? 0}
                </td>
                <td style={{ ...tdStyle(i), textAlign: 'center' }}>
                  {(b.won_count ?? 0) > 0 ? (
                    <span style={{ color: 'var(--accent)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                      {b.won_count}
                    </span>
                  ) : <span style={{ color: 'var(--text3)' }}>0</span>}
                </td>
                <td style={{ ...tdStyle(i), fontWeight: 700, color: 'var(--accent2)', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                  {fmtMoneyCompact(b.total_bid_amount, b.primary_currency || 'USD')}
                </td>
                <td style={{ ...tdStyle(i), color: 'var(--text3)', fontFamily: 'var(--font-mono)', fontSize: 12, whiteSpace: 'nowrap' }}>
                  {fmtDate(b.last_bid_date)}
                </td>
                <td style={{ ...tdStyle(i), width: 36 }}>
                  <span style={{ color: 'var(--text3)', fontSize: 16 }}>&gt;</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: 14,
        flexWrap: 'wrap',
        gap: 8,
        fontSize: 13,
        color: 'var(--text3)',
      }}>
        <span>Page {page} of {totalPages} with {total.toLocaleString()} total bidders</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
            style={{ ...btnStyle(false), opacity: page <= 1 ? 0.4 : 1 }}
          >
            Prev
          </button>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            style={{ ...btnStyle(false), opacity: page >= totalPages ? 0.4 : 1 }}
          >
            Next
          </button>
        </div>
      </div>

      {selected && (
        <>
          <div
            onClick={() => setSelected(null)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 998 }}
          />
          <BidderDetail
            bidder={selected}
            onClose={() => setSelected(null)}
            onSaved={() => { fetchBidders(); setSelected(null) }}
            onDeleted={() => { fetchBidders(); setSelected(null) }}
          />
        </>
      )}
    </div>
  )
}
