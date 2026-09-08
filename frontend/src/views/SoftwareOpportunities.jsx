import { useState } from 'react'
import { Cpu, Download, ExternalLink, RefreshCw, Sparkles } from 'lucide-react'
import { useApi, buildUrl } from '../hooks/useApi.js'
import { apiPost } from '../api.js'

export default function SoftwareOpportunities() {
  const [category, setCategory] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState('')
  const url = buildUrl('/api/software-opportunities', { product_category: category, page_size: 50 })
  const { data, loading, error } = useApi(url, [refreshKey])

  const classifyPending = async () => {
    setRunning(true); setMessage('')
    try {
      const result = await apiPost('/software-opportunities/classify-pending?limit=10')
      setMessage(`Classified ${result.classified.length} notices${result.failed.length ? `; ${result.failed.length} need attention` : ''}.`)
      setRefreshKey(key => key + 1)
    } catch (err) { setMessage(err.message) } finally { setRunning(false) }
  }
  const exportDemand = () => {
    window.location.href = buildUrl('/api/software-opportunities/export', { product_category: category })
  }

  return <div style={{ padding: 28, maxWidth: 1500, margin: '0 auto' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap', marginBottom: 22 }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, color: 'var(--accent)' }}><Cpu size={20} /><span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, letterSpacing: '.08em' }}>PRODUCT INTELLIGENCE</span></div>
        <h1 style={{ margin: '8px 0 5px', fontSize: 26 }}>Software Opportunities</h1>
        <p style={{ margin: 0, color: 'var(--text2)' }}>AI classifies the requested deliverable from full tender context. Product demand counts show how often a similar category was requested.</p>
      </div>
      <button onClick={exportDemand} style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '10px 14px', borderRadius: 8, cursor: 'pointer' }}><Download size={15} />Export demand</button>
      <button onClick={classifyPending} disabled={running} style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#0d2b1e', border: '1px solid #00d4aa', color: '#00d4aa', padding: '10px 14px', borderRadius: 8, cursor: running ? 'wait' : 'pointer' }}>
        {running ? <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Sparkles size={15} />}{running ? 'Classifying…' : 'Classify next 10'}
      </button>
    </div>
    {message && <div style={{ marginBottom: 14, color: 'var(--text2)', fontSize: 13 }}>{message}</div>}
    <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 18 }}>
      <label style={{ color: 'var(--text3)', fontSize: 12 }}>Product category</label>
      <input value={category} onChange={e => setCategory(e.target.value)} placeholder="e.g. identity system" style={{ width: 260, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
    </div>
    {loading && <div style={{ color: 'var(--text2)' }}>Loading software opportunities…</div>}
    {error && <div style={{ color: '#ff7777' }}>{error}</div>}
    {!loading && !error && <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ padding: '12px 16px', color: 'var(--text2)', fontSize: 13 }}>{data?.total || 0} classified software opportunities</div>
      {(data?.data || []).map(row => <div key={row.id} style={{ padding: '15px 16px', borderTop: '1px solid var(--border)', display: 'grid', gridTemplateColumns: 'minmax(300px, 2fr) 1fr 110px 100px 32px', gap: 16, alignItems: 'center' }}>
        <div><div style={{ fontWeight: 600 }}>{row.title}</div><div style={{ marginTop: 4, color: 'var(--text3)', fontSize: 12 }}>{row.country} · {row.notice_date || 'No date'} · {row.software_work_type}</div><div style={{ marginTop: 5, color: 'var(--text2)', fontSize: 12 }}>{row.software_reason}</div></div>
        <div><div style={{ color: 'var(--accent)', fontSize: 13 }}>{row.software_product_category || 'Uncategorised'}</div><div style={{ color: 'var(--text3)', fontSize: 12 }}>{row.software_product_name}</div></div>
        <div style={{ color: 'var(--text2)', fontSize: 12 }}>Demand: <strong>{row.category_demand_count}</strong><div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 3 }}>{row.demand_countries || 'No country data'}</div></div>
        <div style={{ color: row.software_confidence === 'high' ? '#00d4aa' : '#f0a500', fontSize: 12 }}>{row.software_confidence} confidence</div>
        <a href={row.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}><ExternalLink size={16} /></a>
      </div>)}
    </div>}
  </div>
}
