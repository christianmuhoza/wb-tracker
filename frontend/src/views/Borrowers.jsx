import { useState, useEffect, useMemo } from 'react'
import { Search, X, ExternalLink, ChevronLeft, ChevronRight, Download } from 'lucide-react'

const COLORS = { IFB: '#00d4aa', REOI: '#7c6fff', 'Contract Award': '#f0a500', Award: '#f0a500' }
const PAGE_SIZE = 25

const EXPORT_FIELD_OPTIONS = [
  { key: 'borrower', label: 'Institution Name' },
  { key: 'country', label: 'Country' },
  { key: 'total_notices', label: 'Total Notices' },
  { key: 'ifb_count', label: 'IFB Notices' },
  { key: 'reoi_count', label: 'REOI Notices' },
  { key: 'award_count', label: 'Award Notices' },
  { key: 'first_notice_date', label: 'First Notice Date' },
  { key: 'last_notice_date', label: 'Last Notice Date' },
  { key: 'recent_30d', label: '30-Day Activity' },
]

const DEFAULT_EXPORT_FIELDS = [
  'borrower', 'country', 'total_notices', 'ifb_count', 'reoi_count',
  'award_count', 'first_notice_date', 'last_notice_date', 'recent_30d',
]

function Badge({ type }) {
  return (
    <span style={{
      fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 4,
      background: `${COLORS[type] || '#555'}22`, color: COLORS[type] || '#aaa',
      fontWeight: 600, letterSpacing: '0.05em', whiteSpace: 'nowrap'
    }}>{type}</span>
  )
}

function Flag({ country }) {
  const code = (country || '').slice(0, 2).toLowerCase()
  return (
    <img
      src={`https://flagcdn.com/20x15/${code}.png`}
      alt={country}
      style={{ width: 20, height: 15, borderRadius: 2, objectFit: 'cover' }}
      onError={(e) => { e.target.style.display = 'none' }}
    />
  )
}

function StatPill({ label, value, accent }) {
  return (
    <div style={{
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '10px 16px', minWidth: 100,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: accent || 'var(--text)' }}>{value}</div>
    </div>
  )
}

const fmtMoney = (n, currency) => {
  if (n === null || n === undefined || Number(n) === 0) return null
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency: currency || 'USD',
      maximumFractionDigits: 2,
    }).format(Number(n))
  } catch {
    return `${currency || ''} ${Number(n).toLocaleString('en-US')}`
  }
}

function InstitutionDetail({ borrower, country, summary, onClose }) {
  const [notices, setNotices] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const controller = new AbortController()
    const params = new URLSearchParams({ borrower, country, page_size: '50' })
    fetch(`/api/notices?${params.toString()}`, { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json() })
      .then(d => setNotices(d.data || []))
      .catch(() => { if (!controller.signal.aborted) setNotices([]) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [borrower, country])

  const total = summary?.total_notices ?? notices.length
  const ifbCount = summary?.ifb_count ?? notices.filter(n => n.notice_type === 'IFB').length
  const reoiCount = summary?.reoi_count ?? notices.filter(n => n.notice_type === 'REOI').length
  const awardCount = summary?.award_count ?? notices.filter(n => n.notice_type === 'Contract Award' || n.notice_type === 'Award').length
  const totalAwardValue = notices.reduce((sum, n) => {
    const amt = n.award_amount ?? n.contract_amount
    return sum + (amt != null ? Number(amt) : 0)
  }, 0)

  return (
    <aside style={{
      position: 'fixed', top: 0, right: 0, width: 'min(620px, 96vw)',
      height: '100vh', background: 'var(--surface)',
      borderLeft: '1px solid var(--border)', overflowY: 'auto',
      zIndex: 999, boxShadow: 'var(--shadow)',
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: '22px 24px 18px',
        borderBottom: '1px solid var(--border)',
        background: 'linear-gradient(180deg, color-mix(in srgb, var(--accent) 14%, var(--surface)) 0%, var(--surface) 100%)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)', marginBottom: 4, textTransform: 'uppercase' }}>
              Host Institution
            </div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: 'var(--text)', wordBreak: 'break-word' }}>
              {borrower}
            </h2>
            {country && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
                <Flag country={country} />
                <span style={{ color: 'var(--text2)', fontSize: 13 }}>{country}</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--surface2)', border: '1px solid var(--border)',
              color: 'var(--text2)', borderRadius: 10, padding: '7px 12px', fontSize: 12,
            }}
          >
            Close
          </button>
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          <StatPill label="Total Notices" value={total.toLocaleString()} />
          <StatPill label="IFB" value={ifbCount.toLocaleString()} accent={COLORS.IFB} />
          <StatPill label="REOI" value={reoiCount.toLocaleString()} accent={COLORS.REOI} />
          <StatPill label="Awards" value={awardCount.toLocaleString()} accent="#f0a500" />
          {totalAwardValue > 0 && (
            <StatPill label="Total Value" value={fmtMoney(totalAwardValue, 'USD')} accent="#00c853" />
          )}
        </div>
      </div>

      <div style={{ padding: '16px 24px', flex: 1, overflowY: 'auto' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', marginBottom: 12 }}>
          Recent Notices ({total.toLocaleString()})
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text3)' }}>Loading notices...</div>
        ) : notices.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text3)' }}>No notices found for this institution in this country.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {notices.map(n => (
              <div key={n.id} style={{
                border: '1px solid var(--border)', borderRadius: 10, padding: 14,
                background: 'var(--surface2)',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', lineHeight: 1.4 }}>
                    {n.title || '--'}
                  </div>
                  <Badge type={n.notice_type} />
                </div>
                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)', alignItems: 'center' }}>
                  <span>{n.project_id || '--'}</span>
                  <span>{n.notice_date || '--'}</span>
                  {n.submission_date && <span>Deadline: {n.submission_date}</span>}
                  {n.status && (
                    <span style={{
                      color: n.status === 'Active' ? '#00d4aa' : n.status === 'Awarded' ? '#7c6fff' : 'var(--text3)',
                      fontWeight: 600,
                    }}>
                      {n.status}
                    </span>
                  )}
                  {n.url && (
                    <a href={n.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', display: 'flex' }}>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
                {n.procurement_method && (
                  <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text3)' }}>
                    Method: {n.procurement_method}
                  </div>
                )}
                {(() => {
                  const amt = n.award_amount ?? n.contract_amount;
                  return amt != null && Number(amt) > 0 ? (
                    <div style={{ marginTop: 6, fontSize: 12, color: '#f0a500', fontWeight: 700 }}>
                      {fmtMoney(amt, n.award_currency || n.currency)}
                    </div>
                  ) : null
                })()}
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  )
}

export default function Borrowers() {
  const [data, setData] = useState({ data: [], total: 0, available_countries: [] })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [noticeType, setNoticeType] = useState('')
  const [page, setPage] = useState(1)
  const [detailRow, setDetailRow] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [showFieldSelector, setShowFieldSelector] = useState(false)
  const [exportFormat, setExportFormat] = useState('xlsx')
  const [selectedExportFields, setSelectedExportFields] = useState(DEFAULT_EXPORT_FIELDS)
  const [showQualifiedExport, setShowQualifiedExport] = useState(false)
  const [qualifiedMinAwards, setQualifiedMinAwards] = useState(3)
  const [qualifiedTechOnly, setQualifiedTechOnly] = useState(false)
  const [qualifiedExporting, setQualifiedExporting] = useState(false)

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))

  const inputStyle = useMemo(() => ({
    background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)',
    borderRadius: 10, padding: '8px 12px', fontSize: 13, outline: 'none', fontFamily: 'inherit'
  }), [])

  const btnStyle = (active) => ({
    background: active ? 'var(--accent)' : 'var(--surface2)',
    border: `1px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
    color: active ? 'var(--surface)' : 'var(--text2)',
    borderRadius: 10, padding: '8px 14px', fontSize: 13, fontWeight: active ? 700 : 500,
  })

  const thStyle = {
    textAlign: 'left', padding: '12px 14px', fontSize: 11, color: 'var(--text3)',
    textTransform: 'uppercase', letterSpacing: '0.06em',
    borderBottom: '1px solid var(--border)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap',
    background: 'var(--surface)',
  }

  const tdStyle = (i) => ({
    padding: '12px 14px', borderBottom: '1px solid var(--border)',
    background: i % 2 === 0 ? 'color-mix(in srgb, var(--surface2) 38%, transparent)' : 'transparent',
    verticalAlign: 'middle', fontSize: 13,
  })

  const fetchBorrowers = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) })
      if (search) params.set('search', search)
      if (country) params.set('country', country)
      if (noticeType) params.set('notice_type', noticeType)
      const res = await fetch(`/api/borrowers?${params.toString()}`)
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setData({ data: [], total: 0, available_countries: [] })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchBorrowers()
  }, [page])

  const handleFilter = () => {
    setPage(1)
    fetchBorrowers()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleFilter()
  }

  const openDetail = (row) => {
    setDetailRow(row)
  }

  const handleExport = async (format) => {
    setExportFormat(format)
    setShowFieldSelector(true)
  }

  const doExport = async () => {
    setExporting(true)
    setShowFieldSelector(false)
    try {
      const params = new URLSearchParams({ format: exportFormat, fields: selectedExportFields.join(',') })
      if (search) params.set('search', search)
      if (country) params.set('country', country)
      if (noticeType) params.set('notice_type', noticeType)
      const res = await fetch(`/api/borrowers/export?${params.toString()}`)
      if (!res.ok) throw new Error()
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      const filename = match ? match[1] : `WB_Borrowers.${exportFormat}`
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Export failed. Please try again.')
    } finally {
      setExporting(false)
    }
  }

  const doQualifiedExport = async () => {
    setQualifiedExporting(true)
    setShowQualifiedExport(false)
    try {
      const params = new URLSearchParams({
        min_awards: String(qualifiedMinAwards),
        tech_only: String(qualifiedTechOnly),
      })
      const res = await fetch(`/api/borrowers/export/qualified?${params.toString()}`)
      if (!res.ok) throw new Error()
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      const filename = match ? match[1] : 'Qualified_Institutions.xlsx'
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Export failed. Please try again.')
    } finally {
      setQualifiedExporting(false)
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 24, color: 'var(--text)' }}>
            Host Institutions (Borrowers)
          </h2>
          <p style={{ margin: '4px 0 0', color: 'var(--text3)', fontSize: 13 }}>
            {data.total.toLocaleString()} institution–country pairs that issue World Bank procurement opportunities
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => handleExport('csv')} disabled={exporting} style={btnStyle(false)}>
            <Download size={13} style={{ marginRight: 4 }} />CSV
          </button>
          <button onClick={() => handleExport('xlsx')} disabled={exporting} style={btnStyle(true)}>
            <Download size={13} style={{ marginRight: 4 }} />{exporting ? 'Exporting...' : 'Excel'}
          </button>
          <button onClick={() => setShowQualifiedExport(true)} disabled={qualifiedExporting} style={{
            background: 'linear-gradient(135deg, #1B5E20, #2E7D32)',
            border: '1px solid #43A047',
            color: '#fff',
            borderRadius: 10, padding: '8px 14px', fontSize: 13, fontWeight: 600,
          }}>
            <Download size={13} style={{ marginRight: 4 }} />{qualifiedExporting ? 'Exporting...' : 'Qualified Export'}
          </button>
        </div>
      </div>

      <div style={{
        display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap', alignItems: 'center',
        padding: 14, borderRadius: 14, background: 'var(--surface)', border: '1px solid var(--border)',
      }}>
        <div style={{ position: 'relative', flex: '1 1 260px' }}>
          <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text3)' }} />
          <input
            style={{ ...inputStyle, width: '100%', paddingLeft: 30, boxSizing: 'border-box' }}
            placeholder="Search institution name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <select style={{ ...inputStyle, minWidth: 170, flex: '0 1 200px' }} value={country} onChange={e => { setCountry(e.target.value); setPage(1) }}>
          <option value="">All Countries</option>
          {data.available_countries.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select style={{ ...inputStyle, minWidth: 150, flex: '0 1 180px' }} value={noticeType} onChange={e => { setNoticeType(e.target.value); setPage(1) }}>
          <option value="">All Notice Types</option>
          <option value="IFB">IFB</option>
          <option value="REOI">REOI</option>
          <option value="Contract Award">Contract Award</option>
        </select>
        <button onClick={handleFilter} style={btnStyle(true)}>
          <Search size={13} style={{ marginRight: 4 }} />Search
        </button>
        <button onClick={() => { setSearch(''); setCountry(''); setNoticeType(''); setPage(1) }} style={btnStyle(false)}>
          <X size={13} style={{ marginRight: 4 }} />Reset
        </button>
      </div>

      <div style={{ border: '1px solid var(--border)', borderRadius: 16, overflow: 'hidden', background: 'var(--surface)', boxShadow: 'var(--shadow)' }}>
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <table style={{ width: '100%', minWidth: 1060, borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Institution Name', 'Country', 'Total', 'IFB', 'REOI', 'Awards', 'First Notice', 'Last Notice', '30d Activity', ''].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={10} style={{ ...tdStyle(0), textAlign: 'center', padding: 32, color: 'var(--text3)' }}>Loading...</td></tr>
              ) : data.data.length === 0 ? (
                <tr><td colSpan={10} style={{ ...tdStyle(0), textAlign: 'center', padding: 32, color: 'var(--text3)' }}>No institutions found.</td></tr>
              ) : data.data.map((row, i) => (
                <tr
                  key={`${row.borrower}||${row.country}`}
                  onClick={() => openDetail(row)}
                  style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                >
                  <td style={{ ...tdStyle(i), fontWeight: 600, color: 'var(--text)' }}>
                    {row.borrower}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text2)' }}>
                    {row.country || '--'}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)' }}>
                    {row.total_notices?.toLocaleString()}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', color: COLORS.IFB }}>
                    {row.ifb_count?.toLocaleString()}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', color: COLORS.REOI }}>
                    {row.reoi_count?.toLocaleString()}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', color: '#f0a500' }}>
                    {row.award_count?.toLocaleString()}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text3)' }}>
                    {row.first_notice_date || '--'}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text3)' }}>
                    {row.last_notice_date || '--'}
                  </td>
                  <td style={{ ...tdStyle(i), fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
                    <span style={{
                      color: row.recent_30d > 0 ? '#00d4aa' : 'var(--text3)',
                      fontWeight: row.recent_30d > 0 ? 700 : 400,
                    }}>
                      {row.recent_30d}
                    </span>
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
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginTop: 14, flexWrap: 'wrap', gap: 8, fontSize: 13, color: 'var(--text3)',
      }}>
        <span>Page {page} of {totalPages} with {data.total.toLocaleString()} total institution–country entries</span>
        <div style={{ display: 'flex', gap: 6 }}>
          <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} style={{ ...btnStyle(false), opacity: page <= 1 ? 0.4 : 1 }}>
            <ChevronLeft size={13} style={{ marginRight: 4 }} />Prev
          </button>
          <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} style={{ ...btnStyle(false), opacity: page >= totalPages ? 0.4 : 1 }}>
            Next <ChevronRight size={13} style={{ marginLeft: 4 }} />
          </button>
        </div>
      </div>

      {detailRow && (
        <>
          <div onClick={() => setDetailRow(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 998 }} />
          <InstitutionDetail
            borrower={detailRow.borrower}
            country={detailRow.country}
            summary={detailRow}
            onClose={() => setDetailRow(null)}
          />
        </>
      )}

      {showFieldSelector && (
        <>
          <div onClick={() => setShowFieldSelector(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 999 }} />
          <div style={{
            position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
            zIndex: 1000, background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 24, minWidth: 380, maxWidth: 500,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ margin: 0, color: 'var(--text)', fontSize: 18, fontWeight: 600 }}>
                Select Fields for Export ({exportFormat.toUpperCase()})
              </h3>
              <button onClick={() => setShowFieldSelector(false)} style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 20, cursor: 'pointer', padding: 4 }}>
                <X size={16} />
              </button>
            </div>
            <div style={{ marginBottom: 16 }}>
              <button onClick={() => setSelectedExportFields(EXPORT_FIELD_OPTIONS.map(f => f.key))} style={{ background: '#0d2b1e', color: '#00d4aa', border: '1px solid #00d4aa', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer', marginRight: 8 }}>
                Select All
              </button>
              <button onClick={() => setSelectedExportFields(DEFAULT_EXPORT_FIELDS)} style={{ background: '#1a2235', color: 'var(--text3)', border: '1px solid var(--border)', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer', marginRight: 8 }}>
                Reset Defaults
              </button>
              <button onClick={() => setSelectedExportFields([])} style={{ background: '#2b0d0d', color: '#ff6666', border: '1px solid #ff4444', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer' }}>
                Clear
              </button>
            </div>
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8,
              maxHeight: 360, overflowY: 'auto', padding: 8,
              border: '1px solid var(--border)', borderRadius: 8,
            }}>
              {EXPORT_FIELD_OPTIONS.map(field => (
                <label key={field.key} style={{
                  display: 'flex', alignItems: 'center', padding: 8, cursor: 'pointer',
                  borderRadius: 4, transition: 'background 0.2s',
                }}
                  onMouseOver={(e) => { e.currentTarget.style.background = 'var(--surface2)' }}
                  onMouseOut={(e) => { e.currentTarget.style.background = 'transparent' }}
                >
                  <input
                    type="checkbox"
                    checked={selectedExportFields.includes(field.key)}
                    onChange={() => setSelectedExportFields(prev =>
                      prev.includes(field.key) ? prev.filter(f => f !== field.key) : [...prev, field.key]
                    )}
                    style={{ marginRight: 8, cursor: 'pointer' }}
                  />
                  <span style={{ fontSize: 13 }}>{field.label}</span>
                </label>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 20 }}>
              <button onClick={() => setShowFieldSelector(false)} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', borderRadius: 6, padding: '8px 16px', fontSize: 12, cursor: 'pointer' }}>
                Cancel
              </button>
              <button onClick={doExport} disabled={selectedExportFields.length === 0 || exporting} style={{
                background: selectedExportFields.length > 0 ? '#0d2b1e' : '#1a1a1a',
                color: selectedExportFields.length > 0 ? '#00d4aa' : 'var(--text3)',
                border: `1px solid ${selectedExportFields.length > 0 ? '#00d4aa' : 'var(--border)'}`,
                borderRadius: 6, padding: '8px 16px', fontSize: 12, cursor: selectedExportFields.length > 0 && !exporting ? 'pointer' : 'not-allowed',
                fontWeight: 600,
              }}>
                {exporting ? 'Exporting...' : `Export ${selectedExportFields.length} fields`}
              </button>
            </div>
          </div>
        </>
      )}

      {showQualifiedExport && (
        <>
          <div onClick={() => setShowQualifiedExport(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 999 }} />
          <div style={{
            position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
            zIndex: 1000, background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 24, minWidth: 380, maxWidth: 460,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ margin: 0, color: 'var(--text)', fontSize: 18, fontWeight: 600 }}>
                Qualified Institutions Export
              </h3>
              <button onClick={() => setShowQualifiedExport(false)} style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 20, cursor: 'pointer', padding: 4 }}>
                <X size={16} />
              </button>
            </div>
            <p style={{ margin: '0 0 16px', color: 'var(--text3)', fontSize: 13, lineHeight: 1.5 }}>
              Export host institutions with at least N awarded tenders.
              Each sheet = one country. Each row = one awarded notice with Project ID &amp; Reference Number.
            </p>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: 'var(--text2)', fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Minimum Awarded Tenders
              </label>
              <input
                type="number"
                min={1}
                value={qualifiedMinAwards}
                onChange={e => setQualifiedMinAwards(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  ...inputStyle, width: 80,
                }}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13, color: 'var(--text)' }}>
                <input
                  type="checkbox"
                  checked={qualifiedTechOnly}
                  onChange={e => setQualifiedTechOnly(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                Tech-related notices only
              </label>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button onClick={() => setShowQualifiedExport(false)} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', borderRadius: 6, padding: '8px 16px', fontSize: 12, cursor: 'pointer' }}>
                Cancel
              </button>
              <button onClick={doQualifiedExport} disabled={qualifiedExporting} style={{
                background: 'linear-gradient(135deg, #1B5E20, #2E7D32)',
                color: '#fff',
                border: '1px solid #43A047',
                borderRadius: 6, padding: '8px 16px', fontSize: 12, cursor: qualifiedExporting ? 'not-allowed' : 'pointer',
                fontWeight: 600,
              }}>
                {qualifiedExporting ? 'Exporting...' : `Export (>=${qualifiedMinAwards} awards)`}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}