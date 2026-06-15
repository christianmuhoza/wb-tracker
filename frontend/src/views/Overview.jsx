import { useCallback, useEffect, useMemo, useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, CartesianGrid
} from 'recharts'
import {
  TrendingUp, Globe, FileText, Clock, ExternalLink, RefreshCw,
  CheckCircle, AlertCircle, Loader, Activity, Database, CalendarClock, ShieldAlert
} from 'lucide-react'

const COLORS = { IFB: '#00d4aa', REOI: '#7c6fff', 'Contract Award': '#f0a500', Award: '#f0a500' }
const STATUS_COLORS = {
  Active: '#00d4aa',
  Awarded: '#7c6fff',
  Cancelled: '#ff6666',
  Closed: '#8fa3c0',
  Pending: '#f0a500',
}
const SCORE_COLORS = { High: '#00d4aa', Moderate: '#3db2ff', Low: '#f0a500', Inactive: '#ff6666' }
const FETCH_STATUS_COLORS = {
  success: '#00d4aa',
  no_recent_notices: '#f0a500',
  no_data: '#ff9f43',
  failed: '#ff6666',
  running: '#3db2ff',
  not_started: '#8fa3c0',
}

function Section({ title, children }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24 }}>
      <div style={{ fontFamily: 'var(--font-head)', fontSize: 14, fontWeight: 600, color: 'var(--text2)', marginBottom: 20, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function StatCard({ label, value, sub, icon: Icon, accent }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '20px 24px',
      display: 'flex', alignItems: 'flex-start', gap: 16,
      borderTop: `2px solid ${accent || 'var(--accent)'}`,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10,
        background: `${accent || 'var(--accent)'}18`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
      }}>
        <Icon size={18} color={accent || 'var(--accent)'} />
      </div>
      <div>
        <div style={{ fontFamily: 'var(--font-head)', fontSize: 28, fontWeight: 700, lineHeight: 1 }}>
          {value ?? '--'}
        </div>
        <div style={{ color: 'var(--text2)', fontSize: 13, marginTop: 4 }}>{label}</div>
        {sub && <div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 2, fontFamily: 'var(--font-mono)' }}>{sub}</div>}
      </div>
    </div>
  )
}

function BreakdownTable({ rows, columns, emptyMessage = 'No data available.' }) {
  if (!rows.length) {
    return <div style={{ color: 'var(--text3)', fontSize: 13 }}>{emptyMessage}</div>
  }

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          {columns.map(col => (
            <th key={col.key} style={{ textAlign: col.align || 'left', padding: '8px 10px', fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index} style={{ borderBottom: '1px solid var(--border)', background: index % 2 === 0 ? 'transparent' : 'var(--surface2)' }}>
            {columns.map(col => (
              <td key={col.key} style={{ padding: '9px 10px', fontSize: 12, color: 'var(--text2)', fontFamily: col.mono ? 'var(--font-mono)' : 'inherit', textAlign: col.align || 'left', verticalAlign: 'top' }}>
                {col.render ? col.render(row) : row[col.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function CountryPills({ countries, color, emptyMessage }) {
  if (!countries.length) {
    return <div style={{ color: 'var(--text3)', fontSize: 13 }}>{emptyMessage}</div>
  }

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {countries.map(country => (
        <span key={country} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', padding: '5px 9px', borderRadius: 999, background: `${color}22`, color, border: `1px solid ${color}55`, letterSpacing: '0.03em' }}>
          {country}
        </span>
      ))}
    </div>
  )
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 170 }}>
      <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px', fontSize: 13, outline: 'none', cursor: 'pointer' }}>
        <option value="">All</option>
        {options.map(option => <option key={option} value={option}>{option}</option>)}
      </select>
    </div>
  )
}

function HealthRunCard({ run }) {
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 12, background: 'var(--surface2)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ fontSize: 12, color: 'var(--text)' }}>{run.run_at || '--'}</div>
        <div style={{ fontSize: 11, color: run.success ? '#00d4aa' : '#ff6666', fontFamily: 'var(--font-mono)' }}>
          {run.success ? 'Success' : 'Failed'}
        </div>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, color: 'var(--text2)' }}>{run.country || '--'}</div>
      <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>
        fetched {run.fetched ?? 0} | new {run.new_records ?? 0}
      </div>
      {run.error_msg && <div style={{ marginTop: 6, fontSize: 11, color: '#ffb3b3' }}>{run.error_msg}</div>}
    </div>
  )
}

function CountryFetchCoverage({ rows }) {
  if (!rows.length) {
    return <div style={{ color: 'var(--text3)', fontSize: 13 }}>No country fetch status has been recorded yet.</div>
  }

  return (
    <BreakdownTable
      rows={rows}
      columns={[
        { key: 'country', label: 'Country' },
        {
          key: 'status',
          label: 'Status',
          render: row => (
            <span style={{ color: FETCH_STATUS_COLORS[row.status] || 'var(--text2)', fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: 11 }}>
              {String(row.status || 'not_started').replaceAll('_', ' ')}
            </span>
          ),
        },
        { key: 'row_count', label: 'Rows', align: 'right', mono: true, render: row => Number(row.row_count || 0).toLocaleString() },
        { key: 'last_notice_date', label: 'Last Notice', mono: true, render: row => row.last_notice_date || '--' },
        { key: 'explanation', label: 'Explanation', render: row => row.explanation || '--' },
      ]}
    />
  )
}

const tipStyle = {
  background: '#1a2235', border: '1px solid #1f2d45', borderRadius: 8,
  color: '#e2eaf8', fontSize: 12, fontFamily: 'DM Mono, monospace'
}

function buildDashboardUrl(refreshKey, filters) {
  const params = new URLSearchParams({ t: String(refreshKey) })
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '') params.set(key, value)
  })
  return `/api/dashboard?${params.toString()}`
}

function FetchButton({ onDone }) {
  const [state, setState] = useState('idle')
  const [log, setLog] = useState('')
  const [open, setOpen] = useState(false)
  const [startedAt, setStartedAt] = useState(null)

  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/fetch/status')
      if (!res.ok) throw new Error('Could not read fetch status')
      const data = await res.json()

      if (!data.running && data.last_result) {
        const success = data.last_result?.success
        setState(success ? 'success' : 'error')
        setLog(data.last_result?.stdout || data.last_result?.stderr || '')
        if (success && onDone) onDone()
        return false
      }

      if (!data.running && data.last_finished && data.last_result === null) {
        setState('error')
        setLog('The fetch finished without returning a result from the backend.')
        return false
      }

      if (startedAt && Date.now() - startedAt > 10 * 60 * 1000 + 15000) {
        setState('error')
        setLog('The fetch took too long to complete. Please check the backend logs.')
        return false
      }

      return true
    } catch {
      setState('error')
      setLog('Could not reach the backend while checking fetch status.')
      return false
    }
  }, [onDone, startedAt])

  useEffect(() => {
    if (state !== 'running') return undefined
    const interval = setInterval(async () => {
      const keepGoing = await pollStatus()
      if (!keepGoing) clearInterval(interval)
    }, 2000)
    return () => clearInterval(interval)
  }, [state, pollStatus])

  const trigger = async () => {
    if (state === 'running') return
    setState('running')
    setLog('')
    setOpen(false)
    setStartedAt(Date.now())
    try {
      const res = await fetch('/api/fetch', { method: 'POST' })
      if (!res.ok) throw new Error('Could not start fetch')
      const data = await res.json()
      if (data.status !== 'started' && data.status !== 'already_running') {
        throw new Error(data.message || 'Fetch did not start correctly')
      }
    } catch (error) {
      setState('error')
      setLog(error instanceof Error ? error.message : 'Could not reach the backend.')
    }
  }

  const colors = {
    idle: { bg: 'var(--accent)', border: 'var(--accent)', text: '#fff' },
    running: { bg: '#1a2235', border: 'var(--accent)', text: 'var(--accent)' },
    success: { bg: '#0d2b1e', border: '#00d4aa', text: '#00d4aa' },
    error: { bg: '#2b0d0d', border: '#ff4444', text: '#ff6666' },
  }[state]

  const icons = {
    idle: <RefreshCw size={14} />,
    running: <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />,
    success: <CheckCircle size={14} />,
    error: <AlertCircle size={14} />,
  }

  const labels = { idle: 'Fetch Now', running: 'Fetching...', success: 'Done!', error: 'Failed' }

  return (
    <div style={{ position: 'relative' }}>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      <button onClick={state === 'running' ? undefined : (state !== 'idle' ? () => { setState('idle'); setLog('') } : trigger)} style={{ background: colors.bg, border: `1px solid ${colors.border}`, color: colors.text, borderRadius: 8, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: state === 'running' ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 7, transition: 'all 0.2s', whiteSpace: 'nowrap' }}>
        {icons[state]}
        {labels[state]}
      </button>
      {(state === 'success' || state === 'error') && log && (
        <button onClick={() => setOpen(o => !o)} style={{ position: 'absolute', right: 0, top: '100%', marginTop: 4, background: 'transparent', border: 'none', color: 'var(--text3)', fontSize: 11, cursor: 'pointer', whiteSpace: 'nowrap', padding: '2px 4px' }}>
          {open ? 'hide log' : 'view log'}
        </button>
      )}
      {open && log && (
        <div style={{ position: 'absolute', right: 0, top: 'calc(100% + 28px)', zIndex: 200, background: '#0d1525', border: '1px solid var(--border)', borderRadius: 8, padding: 16, width: 480, maxHeight: 300, overflowY: 'auto', fontFamily: 'var(--font-mono)', fontSize: 11, color: '#8fa3c0', whiteSpace: 'pre-wrap', lineHeight: 1.6, boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
          {log}
        </div>
      )}
    </div>
  )
}

export default function Overview() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [filters, setFilters] = useState({ notice_type: '', status: '', search: '', from_date: '', to_date: '' })
  const [selectedCountry, setSelectedCountry] = useState('')

  const dashboardUrl = useMemo(() => buildDashboardUrl(refreshKey, filters), [refreshKey, filters])
  const countryUrl = useMemo(() => selectedCountry ? buildDashboardUrl(refreshKey, { ...filters, country: selectedCountry }) : null, [refreshKey, filters, selectedCountry])

  const { data, loading, error } = useApi(dashboardUrl, [dashboardUrl])
  const { data: countryData, loading: countryLoading, error: countryError } = useApi(countryUrl, [countryUrl])

  const handleFetchDone = useCallback(() => {
    setTimeout(() => setRefreshKey(k => k + 1), 1000)
  }, [])

  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text3)' }}>Loading dashboard...</div>
  }

  const summary = data?.summary || {}
  const byCountry = data?.by_country || []
  const byType = data?.by_type || []
  const byStatus = data?.by_status || []
  const byMonth = [...(data?.by_month || [])].reverse()
  const topBorrowers = data?.top_borrowers || []
  const recent = data?.recent || []
  const availableCountries = data?.available_countries || []
  const countriesOverview = data?.countries_overview || { configured: [], active: [], inactive: [], configured_count: 0, active_count: 0, inactive_count: 0 }
  const dataQuality = data?.data_quality || {}
  const deadlines = data?.deadlines || { upcoming: [] }
  const fetchHealth = data?.fetch_health || { recent_runs: [] }
  const countryFetchStatuses = fetchHealth.country_statuses || []
  const activityScores = data?.activity_scores || []
  const recentChanges = data?.recent_changes || []
  const apiError = error || data?.error || null

  const countrySummary = countryData?.summary || {}
  const countryTypes = countryData?.by_type || []
  const countryStatuses = countryData?.by_status || []
  const countryBorrowers = countryData?.top_borrowers || []
  const countryRecent = countryData?.recent || []
  const countryByMonth = [...(countryData?.by_month || [])].reverse()
  const countryApiError = countryError || countryData?.error || null

  const lastFetched = summary.last_fetched
    ? new Date(summary.last_fetched).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Never'

  return (
    <div style={{ padding: '32px', maxWidth: 1500 }}>
      <div style={{ marginBottom: 32, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 32, fontWeight: 800, letterSpacing: '-1px' }}>Procurement Overview</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Last synced: {lastFetched} | general intelligence, health, quality, deadlines, changes and borrower insights
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingTop: 4 }}>
          <button onClick={() => setRefreshKey(k => k + 1)} title="Refresh dashboard" style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', borderRadius: 8, padding: '8px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
            <RefreshCw size={13} />
          </button>
          <FetchButton onDone={handleFetchDone} />
        </div>
      </div>

      {apiError && (
        <div style={{ marginBottom: 20, background: '#2b0d0d', border: '1px solid #ff4444', color: '#ffb3b3', borderRadius: 10, padding: '12px 14px', fontSize: 13, lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
          Dashboard data could not be loaded.
          {'\n'}
          {apiError}
        </div>
      )}

      <Section title="Overview Filters">
        <div style={{ display: 'flex', alignItems: 'end', gap: 16, flexWrap: 'wrap' }}>
          <FilterSelect label="Notice Type" value={filters.notice_type} onChange={value => setFilters(current => ({ ...current, notice_type: value }))} options={['IFB', 'REOI', 'Contract Award']} />
          <FilterSelect label="Status" value={filters.status} onChange={value => setFilters(current => ({ ...current, status: value }))} options={['Active', 'Awarded', 'Cancelled', 'Closed', 'Pending', 'Published']} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Search</label>
            <input value={filters.search} onChange={e => setFilters(current => ({ ...current, search: e.target.value }))} placeholder="Project, borrower, title..." style={{ width: 220, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px', fontSize: 13, outline: 'none' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>From Date</label>
            <input type="date" value={filters.from_date} onChange={e => setFilters(current => ({ ...current, from_date: e.target.value }))} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px', fontSize: 13, outline: 'none' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>To Date</label>
            <input type="date" value={filters.to_date} onChange={e => setFilters(current => ({ ...current, to_date: e.target.value }))} style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px', fontSize: 13, outline: 'none' }} />
          </div>
          <button onClick={() => setFilters({ notice_type: '', status: '', search: '', from_date: '', to_date: '' })} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8, padding: '8px 12px', fontSize: 13 }}>Reset Filters</button>
        </div>
      </Section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: 28, marginBottom: 28 }}>
        <StatCard label="Total Notices" value={summary.total?.toLocaleString()} icon={FileText} accent="var(--accent)" />
        <StatCard label="IFB Notices" value={summary.total_ifb?.toLocaleString()} icon={TrendingUp} accent="var(--ifb)" />
        <StatCard label="REOI Notices" value={summary.total_reoi?.toLocaleString()} icon={Globe} accent="var(--reoi)" />
        <StatCard label="Countries Active" value={countriesOverview.active_count} icon={Clock} accent="var(--accent2)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        <StatCard label="Contract Awards" value={summary.total_award?.toLocaleString()} icon={FileText} accent="#f0a500" />
        <StatCard label="Borrowers Seen" value={summary.borrowers?.toLocaleString()} icon={Database} accent="#3db2ff" />
        <StatCard label="Statuses Seen" value={summary.statuses?.toLocaleString()} icon={Activity} accent="#ff7f50" />
        <StatCard label="Configured Countries" value={countriesOverview.configured_count} icon={Globe} accent="#8fa3c0" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 280px', gap: 16, marginBottom: 28 }}>
        <Section title="Notices by Country">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={byCountry} layout="vertical" margin={{ left: 20, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d45" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="country" tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} width={120} />
              <Tooltip contentStyle={tipStyle} />
              <Bar dataKey="ifb_count" name="IFB" stackId="a" fill={COLORS.IFB} />
              <Bar dataKey="reoi_count" name="REOI" stackId="a" fill={COLORS.REOI} />
              <Bar dataKey="award_count" name="Awards" stackId="a" fill={COLORS['Contract Award']} />
            </BarChart>
          </ResponsiveContainer>
        </Section>

        <Section title="Monthly Trend">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={byMonth} margin={{ left: 0, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d45" />
              <XAxis dataKey="month" tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={tipStyle} />
              <Line type="monotone" dataKey="count" stroke="#0099ff" strokeWidth={2} dot={{ fill: '#0099ff', r: 3 }} name="Notices" />
            </LineChart>
          </ResponsiveContainer>
        </Section>

        <Section title="Notice Types">
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 260 }}>
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={byType} dataKey="count" nameKey="notice_type" cx="50%" cy="50%" outerRadius={70} innerRadius={40}>
                  {byType.map(entry => <Cell key={entry.notice_type} fill={COLORS[entry.notice_type] || '#555'} />)}
                </Pie>
                <Tooltip contentStyle={tipStyle} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
              {byType.map(t => (
                <div key={t.notice_type} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text2)' }}>
                  <div style={{ width: 10, height: 10, borderRadius: 2, background: COLORS[t.notice_type] || '#555' }} />
                  {t.notice_type} ({t.count})
                </div>
              ))}
            </div>
          </div>
        </Section>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 28 }}>
        <Section title={`Active Countries (${countriesOverview.active_count || 0})`}>
          <CountryPills countries={countriesOverview.active || []} color="#00d4aa" emptyMessage="No active countries found yet." />
        </Section>
        <Section title={`Non-Active Countries (${countriesOverview.inactive_count || 0})`}>
          <CountryPills countries={countriesOverview.inactive || []} color="#ff6666" emptyMessage="All configured countries currently have notices." />
        </Section>
      </div>

      <div style={{ marginBottom: 28 }}>
        <Section title="Country Fetch Coverage">
          <CountryFetchCoverage rows={countryFetchStatuses} />
        </Section>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 28 }}>
        <Section title="Fetch Health">
          <div style={{ display: 'grid', gap: 10 }}>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>Running: <span style={{ color: fetchHealth.running ? '#00d4aa' : 'var(--text)' }}>{fetchHealth.running ? 'Yes' : 'No'}</span></div>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>Last Triggered: {fetchHealth.last_triggered || '--'}</div>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>Last Finished: {fetchHealth.last_finished || '--'}</div>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>Last Result: {fetchHealth.last_result?.success === true ? 'Success' : fetchHealth.last_result?.success === false ? 'Failed' : '--'}</div>
            <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
              {(fetchHealth.recent_runs || []).map((run, index) => <HealthRunCard key={index} run={run} />)}
            </div>
          </div>
        </Section>

        <Section title="Data Quality">
          <BreakdownTable
            rows={[
              { label: 'Missing Borrower', value: dataQuality.missing_borrower || 0 },
              { label: 'Missing Contact Email', value: dataQuality.missing_contact_email || 0 },
              { label: 'Missing Submission Date', value: dataQuality.missing_submission_date || 0 },
              { label: 'Missing Procurement Method', value: dataQuality.missing_procurement_method || 0 },
            ]}
            columns={[
              { key: 'label', label: 'Metric' },
              { key: 'value', label: 'Count', align: 'right', mono: true, render: row => Number(row.value || 0).toLocaleString() },
            ]}
            emptyMessage="No quality metrics available."
          />
        </Section>

        <Section title="Deadline Intelligence">
          <div style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              <StatCard label="Due in 7 Days" value={deadlines.upcoming_7_days?.toLocaleString()} icon={CalendarClock} accent="#3db2ff" />
              <StatCard label="Due in 30 Days" value={deadlines.upcoming_30_days?.toLocaleString()} icon={CalendarClock} accent="#f0a500" />
              <StatCard label="Overdue Active" value={deadlines.overdue_active?.toLocaleString()} icon={ShieldAlert} accent="#ff6666" />
            </div>
            <BreakdownTable
              rows={deadlines.upcoming || []}
              columns={[
                { key: 'country', label: 'Country' },
                { key: 'project_id', label: 'Project', mono: true, render: row => row.project_id || '--' },
                { key: 'submission_date', label: 'Deadline', mono: true },
              ]}
              emptyMessage="No upcoming deadlines in the next 30 days."
            />
          </div>
        </Section>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr 1fr', gap: 16, marginBottom: 28 }}>
        <Section title="Country Breakdown">
          <BreakdownTable
            rows={byCountry}
            columns={[
              { key: 'country', label: 'Country' },
              { key: 'total_count', label: 'Total', align: 'right', mono: true, render: row => Number(row.total_count || 0).toLocaleString() },
              { key: 'ifb_count', label: 'IFB', align: 'right', mono: true, render: row => Number(row.ifb_count || 0).toLocaleString() },
              { key: 'reoi_count', label: 'REOI', align: 'right', mono: true, render: row => Number(row.reoi_count || 0).toLocaleString() },
              { key: 'award_count', label: 'Awards', align: 'right', mono: true, render: row => Number(row.award_count || 0).toLocaleString() },
            ]}
            emptyMessage="No country stats available."
          />
        </Section>

        <Section title="Status Breakdown">
          <BreakdownTable
            rows={byStatus}
            columns={[
              { key: 'status', label: 'Status', render: row => <span style={{ color: STATUS_COLORS[row.status] || 'var(--text2)', fontWeight: 600 }}>{row.status || '--'}</span> },
              { key: 'count', label: 'Count', align: 'right', mono: true, render: row => Number(row.count || 0).toLocaleString() },
            ]}
            emptyMessage="No status stats available."
          />
        </Section>

        <Section title="Borrower Intelligence">
          <BreakdownTable
            rows={topBorrowers}
            columns={[
              { key: 'borrower', label: 'Borrower' },
              { key: 'count', label: 'Notices', align: 'right', mono: true, render: row => Number(row.count || 0).toLocaleString() },
              { key: 'last_notice_date', label: 'Last', mono: true, render: row => row.last_notice_date || '--' },
            ]}
            emptyMessage="No borrower intelligence available."
          />
        </Section>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 28 }}>
        <Section title="Country Activity Scoring">
          <BreakdownTable
            rows={activityScores}
            columns={[
              { key: 'country', label: 'Country' },
              { key: 'recent_count', label: '30d Notices', align: 'right', mono: true, render: row => Number(row.recent_count || 0).toLocaleString() },
              { key: 'score', label: 'Score', render: row => <span style={{ color: SCORE_COLORS[row.score] || 'var(--text2)', fontWeight: 600 }}>{row.score}</span> },
            ]}
            emptyMessage="No activity scoring available."
          />
        </Section>

        <Section title="Recent Changes">
          <BreakdownTable
            rows={recentChanges}
            columns={[
              { key: 'country', label: 'Country' },
              { key: 'notice_type', label: 'Type', mono: true, render: row => row.notice_type || '--' },
              { key: 'status', label: 'Status', render: row => <span style={{ color: STATUS_COLORS[row.status] || 'var(--text2)', fontWeight: 600 }}>{row.status || '--'}</span> },
              { key: 'updated_at', label: 'Updated', mono: true, render: row => row.updated_at || '--' },
            ]}
            emptyMessage="No recent changes available."
          />
        </Section>
      </div>

      <Section title="Country Drilldown">
        <div style={{ display: 'flex', alignItems: 'end', gap: 16, flexWrap: 'wrap', marginBottom: 20 }}>
          <FilterSelect label="Select Country" value={selectedCountry} onChange={setSelectedCountry} options={availableCountries} />
          {selectedCountry && <button onClick={() => setSelectedCountry('')} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8, padding: '8px 12px', fontSize: 13 }}>Clear</button>}
        </div>
        {!selectedCountry && <div style={{ color: 'var(--text3)', fontSize: 13 }}>Select a country to see its filtered monthly trend, notice types, top borrowers and recent notices while the general dashboard stays visible above.</div>}
        {countryApiError && <div style={{ marginBottom: 12, color: '#ffb3b3', fontSize: 13, whiteSpace: 'pre-wrap' }}>{countryApiError}</div>}
        {selectedCountry && !countryApiError && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
              <StatCard label={`${selectedCountry} Notices`} value={countrySummary.total?.toLocaleString()} icon={FileText} accent="var(--accent)" />
              <StatCard label={`${selectedCountry} IFB`} value={countrySummary.total_ifb?.toLocaleString()} icon={TrendingUp} accent="var(--ifb)" />
              <StatCard label={`${selectedCountry} REOI`} value={countrySummary.total_reoi?.toLocaleString()} icon={Globe} accent="var(--reoi)" />
              <StatCard label={`${selectedCountry} Awards`} value={countrySummary.total_award?.toLocaleString()} icon={Clock} accent="#f0a500" />
            </div>
            {countryLoading ? <div style={{ color: 'var(--text3)', fontSize: 13 }}>Loading {selectedCountry} data...</div> : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                <Section title={`${selectedCountry} Monthly Trend`}>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={countryByMonth} margin={{ left: 0, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2d45" />
                      <XAxis dataKey="month" tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: '#8fa3c0', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={tipStyle} />
                      <Line type="monotone" dataKey="count" stroke="#0099ff" strokeWidth={2} dot={{ fill: '#0099ff', r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </Section>
                <Section title={`${selectedCountry} Notice Types`}>
                  <BreakdownTable rows={countryTypes} columns={[{ key: 'notice_type', label: 'Type', mono: true }, { key: 'count', label: 'Count', align: 'right', mono: true, render: row => Number(row.count || 0).toLocaleString() }]} emptyMessage={`No type stats for ${selectedCountry}.`} />
                </Section>
                <Section title={`${selectedCountry} Statuses`}>
                  <BreakdownTable rows={countryStatuses} columns={[{ key: 'status', label: 'Status', render: row => <span style={{ color: STATUS_COLORS[row.status] || 'var(--text2)', fontWeight: 600 }}>{row.status || '--'}</span> }, { key: 'count', label: 'Count', align: 'right', mono: true, render: row => Number(row.count || 0).toLocaleString() }]} emptyMessage={`No status stats for ${selectedCountry}.`} />
                </Section>
                <Section title={`${selectedCountry} Borrowers`}>
                  <BreakdownTable rows={countryBorrowers} columns={[{ key: 'borrower', label: 'Borrower' }, { key: 'count', label: 'Count', align: 'right', mono: true, render: row => Number(row.count || 0).toLocaleString() }]} emptyMessage={`No borrower stats for ${selectedCountry}.`} />
                </Section>
                <Section title={`${selectedCountry} Recent Notices`}>
                  <BreakdownTable rows={countryRecent} columns={[{ key: 'notice_type', label: 'Type', mono: true }, { key: 'project_id', label: 'Project', mono: true, render: row => row.project_id || '--' }, { key: 'notice_date', label: 'Date', mono: true, render: row => row.notice_date || '--' }]} emptyMessage={`No recent notices for ${selectedCountry}.`} />
                </Section>
              </div>
            )}
          </>
        )}
      </Section>

      <Section title="Recent Notices">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Country', 'Type', 'Title', 'Borrower', 'Project', 'Date', ''].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '8px 12px', fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)', fontWeight: 400, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map((n, i) => (
              <tr key={n.id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'var(--surface2)' }}>
                <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{n.country || '--'}</td>
                <td style={{ padding: '10px 12px' }}>
                  <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 4, background: `${COLORS[n.notice_type] || '#555'}22`, color: COLORS[n.notice_type] || '#aaa', fontWeight: 600, letterSpacing: '0.05em' }}>{n.notice_type || '--'}</span>
                </td>
                <td style={{ padding: '10px 12px', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>{n.title || '--'}</td>
                <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--text2)' }}>{n.borrower || '--'}</td>
                <td style={{ padding: '10px 12px', color: 'var(--text2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>{n.project_id || '--'}</td>
                <td style={{ padding: '10px 12px', color: 'var(--text3)', fontSize: 12, fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>{n.notice_date || '--'}</td>
                <td style={{ padding: '10px 12px' }}>{n.url && <a href={n.url} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a>}</td>
              </tr>
            ))}
            {recent.length === 0 && <tr><td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text3)' }}>No data yet - click Fetch Now above.</td></tr>}
          </tbody>
        </table>
      </Section>
    </div>
  )
}
