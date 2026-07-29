import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bell, CheckCircle, ExternalLink, RefreshCw, ShieldCheck, XCircle } from 'lucide-react'

const fmtDate = (value) => value ? String(value).slice(0, 10) : '--'

const fmtMoney = (amount, currency) => {
  if (!amount || Number(amount) === 0) return '--'
  try {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      maximumFractionDigits: 2,
    }).format(Number(amount))
  } catch {
    return `${currency || ''} ${Number(amount).toLocaleString('en-US')}`.trim()
  }
}

function StatusPill({ status }) {
  const map = {
    auto_matched: { label: 'Auto Matched', color: '#00d4aa', bg: '#0d2b1e' },
    needs_review: { label: 'Needs Review', color: '#f0a500', bg: '#1a1500' },
    confirmed: { label: 'Confirmed', color: '#3db2ff', bg: '#0d1f2b' },
  }
  const item = map[status] || { label: status || 'Unknown', color: 'var(--text3)', bg: 'var(--surface2)' }
  return (
    <span style={{ background: item.bg, color: item.color, border: `1px solid ${item.color}55`, borderRadius: 999, padding: '3px 8px', fontSize: 11, fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
      {item.label}
    </span>
  )
}

function NoticePanel({ label, type, title, projectId, projectName, country, borrower, date, url }) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 14, background: 'var(--surface2)', minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 8 }}>
        <div style={{ color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
        <span style={{ color: type === 'Contract Award' || type === 'Award' ? '#f0a500' : 'var(--accent)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{type || '--'}</span>
      </div>
      <div style={{ color: 'var(--text)', fontWeight: 700, lineHeight: 1.35, marginBottom: 10 }}>{title || '--'}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px', color: 'var(--text2)', fontSize: 12 }}>
        <div><span style={{ color: 'var(--text3)' }}>Project:</span> {projectId || '--'}</div>
        <div><span style={{ color: 'var(--text3)' }}>Date:</span> {fmtDate(date)}</div>
        <div><span style={{ color: 'var(--text3)' }}>Country:</span> {country || '--'}</div>
        <div><span style={{ color: 'var(--text3)' }}>Borrower:</span> {borrower || '--'}</div>
      </div>
      {projectName && <div style={{ marginTop: 8, color: 'var(--text3)', fontSize: 12 }}>{projectName}</div>}
      {url && (
        <a href={url} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 10, fontSize: 12 }}>
          <ExternalLink size={12} /> World Bank notice
        </a>
      )}
    </div>
  )
}

function AlertCard({ alert, onRefresh }) {
  const [busy, setBusy] = useState(null)

  const update = async (action, url, options = {}) => {
    setBusy(action)
    try {
      const res = await fetch(url, options)
      if (!res.ok) throw new Error('Request failed')
      await onRefresh()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div style={{ background: 'var(--surface)', border: `1px solid ${alert.seen_at ? 'var(--border)' : 'var(--accent)'}`, borderRadius: 8, padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 14, marginBottom: 14 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 7 }}>
            {!alert.seen_at && <span style={{ width: 8, height: 8, borderRadius: 999, background: 'var(--accent)', display: 'inline-block' }} />}
            <StatusPill status={alert.match_status} />
            <span style={{ color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>Score {alert.match_score}</span>
            <span style={{ color: 'var(--text3)', fontSize: 11 }}>{alert.matched_reason}</span>
          </div>
          <h3 style={{ margin: 0, color: 'var(--text)', fontSize: 18, lineHeight: 1.3 }}>Opportunity became awarded</h3>
          <p style={{ margin: '5px 0 0', color: 'var(--text3)', fontSize: 12 }}>Created {alert.created_at ? new Date(alert.created_at).toLocaleString() : '--'}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {!alert.seen_at && (
            <button onClick={() => update('seen', `/api/award-alerts/${alert.id}/seen`, { method: 'PUT' })} disabled={!!busy} style={buttonStyle(false)}>
              <CheckCircle size={13} /> Seen
            </button>
          )}
          <button onClick={() => update('confirmed', `/api/award-alerts/${alert.id}/status?match_status=confirmed`, { method: 'PUT' })} disabled={!!busy} style={buttonStyle(false)}>
            <ShieldCheck size={13} /> Confirm
          </button>
          <button onClick={() => update('rejected', `/api/award-alerts/${alert.id}/status?match_status=rejected`, { method: 'PUT' })} disabled={!!busy} style={buttonStyle(true)}>
            <XCircle size={13} /> Reject
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <NoticePanel
          label="Original opportunity"
          type={alert.source_notice_type}
          title={alert.source_title}
          projectId={alert.source_project_id}
          projectName={alert.source_project_name}
          country={alert.source_country}
          borrower={alert.source_borrower}
          date={alert.source_notice_date}
          url={alert.source_url}
        />
        <NoticePanel
          label="Award notice"
          type={alert.award_notice_type}
          title={alert.award_title}
          projectId={alert.award_project_id}
          projectName={alert.award_project_name}
          country={alert.award_country}
          borrower={alert.award_borrower}
          date={alert.award_notice_date}
          url={alert.award_url}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 14, marginTop: 14 }}>
        <div style={summaryBoxStyle}>
          <div style={summaryLabelStyle}>Awarded bidder(s)</div>
          <div style={{ color: 'var(--text)', fontWeight: 700 }}>{alert.awarded_bidders || 'Not extracted yet'}</div>
        </div>
        <div style={summaryBoxStyle}>
          <div style={summaryLabelStyle}>Award amount</div>
          <div style={{ color: '#f0a500', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{fmtMoney(alert.award_amount, alert.award_currency)}</div>
        </div>
      </div>
    </div>
  )
}

const summaryBoxStyle = { border: '1px solid var(--border)', borderRadius: 8, padding: 12, background: 'color-mix(in srgb, var(--surface2) 55%, transparent)' }
const summaryLabelStyle = { color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }

const buttonStyle = (danger = false) => ({
  background: danger ? '#2b0d0d' : 'var(--surface2)',
  border: `1px solid ${danger ? '#ff4444' : 'var(--border)'}`,
  color: danger ? '#ff6666' : 'var(--text2)',
  borderRadius: 8,
  padding: '7px 10px',
  fontSize: 12,
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
})

export default function AwardAlerts() {
  const [alerts, setAlerts] = useState([])
  const [meta, setMeta] = useState({ total: 0, unread: 0 })
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [filter, setFilter] = useState('all')
  const [message, setMessage] = useState('')

  const query = useMemo(() => {
    const params = new URLSearchParams({ page_size: '50' })
    if (filter === 'unread') params.set('unread_only', 'true')
    if (filter === 'review') params.set('status', 'needs_review')
    return params.toString()
  }, [filter])

  const loadAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/award-alerts?${query}`)
      if (!res.ok) throw new Error('Failed to load award alerts')
      const data = await res.json()
      setAlerts(data.data || [])
      setMeta({ total: data.total || 0, unread: data.unread || 0 })
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  const sync = async () => {
    setSyncing(true)
    setMessage('')
    try {
      const res = await fetch('/api/award-alerts/sync', { method: 'POST' })
      if (!res.ok) throw new Error('Sync failed')
      const data = await res.json()
      setMessage(`Sync complete: ${data.created || 0} new alerts, ${data.updated || 0} refreshed.`)
      await loadAlerts()
    } catch {
      setMessage('Could not sync award alerts. Make sure the backend and database are running.')
    } finally {
      setSyncing(false)
    }
  }

  const markAllSeen = async () => {
    await fetch('/api/award-alerts/mark-all-seen', { method: 'POST' })
    await loadAlerts()
  }

  return (
    <div style={{ padding: 28, maxWidth: 1500 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap', marginBottom: 22 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 30, fontWeight: 800, margin: 0 }}>Award Alerts</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontSize: 13 }}>IFB and REOI opportunities that now have matching contract award notices.</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={sync} disabled={syncing} style={{ ...buttonStyle(false), background: 'var(--accent)', borderColor: 'var(--accent)', color: '#fff', fontWeight: 700 }}>
            <RefreshCw size={13} style={syncing ? { animation: 'spin 1s linear infinite' } : undefined} /> {syncing ? 'Syncing...' : 'Sync Alerts'}
          </button>
          <button onClick={markAllSeen} disabled={meta.unread === 0} style={buttonStyle(false)}>
            <CheckCircle size={13} /> Mark All Seen
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(150px, 1fr))', gap: 12, marginBottom: 18 }}>
        <div style={summaryBoxStyle}><div style={summaryLabelStyle}>Visible alerts</div><div style={{ fontSize: 24, fontWeight: 800 }}>{meta.total.toLocaleString()}</div></div>
        <div style={summaryBoxStyle}><div style={summaryLabelStyle}>Unread</div><div style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent)' }}>{meta.unread.toLocaleString()}</div></div>
        <div style={summaryBoxStyle}><div style={summaryLabelStyle}>Current filter</div><div style={{ fontSize: 18, fontWeight: 800 }}>{filter === 'review' ? 'Needs Review' : filter === 'unread' ? 'Unread' : 'All Active'}</div></div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
        {[
          ['all', 'All Active'],
          ['unread', 'Unread'],
          ['review', 'Needs Review'],
        ].map(([key, label]) => (
          <button key={key} onClick={() => setFilter(key)} style={{ ...buttonStyle(false), background: filter === key ? 'var(--accent)' : 'var(--surface2)', borderColor: filter === key ? 'var(--accent)' : 'var(--border)', color: filter === key ? '#fff' : 'var(--text2)' }}>{label}</button>
        ))}
      </div>

      {message && <div style={{ marginBottom: 16, color: message.startsWith('Could') ? '#ffb3b3' : 'var(--accent)', fontSize: 13 }}>{message}</div>}

      {loading ? (
        <div style={{ color: 'var(--text3)', padding: 32, textAlign: 'center' }}>Loading award alerts...</div>
      ) : alerts.length === 0 ? (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 32, textAlign: 'center' }}>
          <Bell size={24} color="var(--text3)" />
          <div style={{ color: 'var(--text)', fontWeight: 700, marginTop: 10 }}>No award alerts yet</div>
          <div style={{ color: 'var(--text3)', fontSize: 13, marginTop: 4 }}>Run Sync Alerts after fetching notices to match awards back to IFB/REOI opportunities.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 14 }}>
          {alerts.map(alert => <AlertCard key={alert.id} alert={alert} onRefresh={loadAlerts} />)}
        </div>
      )}
    </div>
  )
}