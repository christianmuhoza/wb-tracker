import { useState } from 'react'
import { useApi } from '../hooks/useApi.js'
import { Save, Plus, Trash2, RefreshCw, RotateCcw } from 'lucide-react'

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

export default function Settings() {
  const [refreshKey, setRefreshKey] = useState(0)
  const { data: general, loading: generalLoading } = useApi(`/api/settings/general?t=${refreshKey}`, [refreshKey])
  const { data: countries, loading: countriesLoading } = useApi(`/api/settings/countries?t=${refreshKey}`, [refreshKey])
  const { data: countryStatuses, loading: statusesLoading } = useApi(`/api/fetch/countries?t=${refreshKey}`, [refreshKey])
  const [form, setForm] = useState({ baseline_date: '', country_batch: '', request_delay: '', auto_sync_hour: '' })
  const [newCountry, setNewCountry] = useState('')
  const [message, setMessage] = useState('')

  const saveSettings = async () => {
    const payload = {
      baseline_date: form.baseline_date || general?.baseline_date,
      country_batch: Number(form.country_batch || general?.country_batch || 5),
      request_delay: Number(form.request_delay || general?.request_delay || 1.2),
      auto_sync_hour: form.auto_sync_hour || general?.auto_sync_hour,
    }
    const res = await fetch('/api/settings/general', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    setMessage(res.ok ? 'Settings saved.' : 'Could not save settings.')
    setRefreshKey(k => k + 1)
  }

  const addCountry = async () => {
    if (!newCountry.trim()) return
    const res = await fetch('/api/settings/countries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newCountry.trim() }),
    })
    setMessage(res.ok ? `${newCountry.trim()} added.` : `Could not add ${newCountry.trim()}.`)
    setNewCountry('')
    setRefreshKey(k => k + 1)
  }

  const removeCountry = async (name) => {
    const res = await fetch(`/api/settings/countries/${encodeURIComponent(name)}`, { method: 'DELETE' })
    setMessage(res.ok ? `${name} removed.` : `Could not remove ${name}.`)
    setRefreshKey(k => k + 1)
  }

  const backfillCountry = async (name) => {
    const since = form.baseline_date || general?.baseline_date || '2025-01-01'
    const res = await fetch(`/api/fetch/backfill/${encodeURIComponent(name)}?since=${encodeURIComponent(since)}`, { method: 'POST' })
    setMessage(res.ok ? `${name} backfill started from ${since}. Refresh in a moment.` : `Could not start ${name} backfill.`)
    setRefreshKey(k => k + 1)
  }

  const statusColor = (status) => ({
    success: '#00d4aa',
    no_recent_notices: '#f0a500',
    no_data: '#ff9f43',
    failed: '#ff6666',
    running: '#3db2ff',
    not_started: '#8fa3c0',
  }[status] || '#8fa3c0')

  return (
    <div style={{ padding: 32, maxWidth: 1200 }}>
      <div style={{ marginBottom: 32, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 32, fontWeight: 800, letterSpacing: '-1px' }}>Admin Settings</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Manage fetch configuration, baseline date and tracked countries.
          </p>
        </div>
        <button onClick={() => setRefreshKey(k => k + 1)} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', borderRadius: 8, padding: '8px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <RefreshCw size={13} />
        </button>
      </div>

      {message && <div style={{ marginBottom: 20, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 10, padding: '10px 12px', fontSize: 13 }}>{message}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Section title="General Fetch Settings">
          {generalLoading ? <div style={{ color: 'var(--text3)' }}>Loading settings...</div> : (
            <div style={{ display: 'grid', gap: 14 }}>
              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--text3)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>Baseline Date</label>
                <input type="date" defaultValue={general?.baseline_date} onChange={e => setForm(current => ({ ...current, baseline_date: e.target.value }))} style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--text3)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>Country Batch Size</label>
                <input type="number" defaultValue={general?.country_batch} onChange={e => setForm(current => ({ ...current, country_batch: e.target.value }))} style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--text3)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>Request Delay</label>
                <input type="number" step="0.1" defaultValue={general?.request_delay} onChange={e => setForm(current => ({ ...current, request_delay: e.target.value }))} style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 11, color: 'var(--text3)', marginBottom: 4, fontFamily: 'var(--font-mono)' }}>Auto Sync Hour</label>
                <input type="time" defaultValue={general?.auto_sync_hour} onChange={e => setForm(current => ({ ...current, auto_sync_hour: e.target.value }))} style={{ width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
              </div>
              <button onClick={saveSettings} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: '#fff', borderRadius: 8, padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 8, width: 'fit-content' }}>
                <Save size={14} />
                Save Settings
              </button>
            </div>
          )}
        </Section>

        <Section title="Tracked Countries">
          <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
            <input value={newCountry} onChange={e => setNewCountry(e.target.value)} placeholder="Add country..." style={{ flex: 1, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '8px 10px' }} />
            <button onClick={addCountry} style={{ background: 'var(--accent)', border: '1px solid var(--accent)', color: '#fff', borderRadius: 8, padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Plus size={14} />
              Add
            </button>
          </div>
          {countriesLoading ? <div style={{ color: 'var(--text3)' }}>Loading countries...</div> : (
            <div style={{ display: 'grid', gap: 10 }}>
              {(countries || []).map(country => (
                <div key={country.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface2)', padding: '10px 12px' }}>
                  <div>
                    <div style={{ color: 'var(--text)', fontSize: 13 }}>{country.name}</div>
                    <div style={{ color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{country.added_at || '--'}</div>
                  </div>
                  <button onClick={() => removeCountry(country.name)} style={{ background: 'transparent', border: '1px solid #5c2d2d', color: '#ff6666', borderRadius: 8, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Trash2 size={12} />
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>

      <div style={{ marginTop: 16 }}>
        <Section title="Country Fetch Coverage">
          {statusesLoading ? <div style={{ color: 'var(--text3)' }}>Loading country coverage...</div> : (
            <div style={{ display: 'grid', gap: 10 }}>
              {(countryStatuses || []).map(country => (
                <div key={country.country} style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.8fr 0.7fr 1.5fr auto', gap: 12, alignItems: 'center', border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface2)', padding: '10px 12px' }}>
                  <div>
                    <div style={{ color: 'var(--text)', fontSize: 13 }}>{country.country}</div>
                    <div style={{ color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                      {country.first_notice_date || '--'} to {country.last_notice_date || '--'}
                    </div>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: statusColor(country.status), textTransform: 'uppercase' }}>
                    {String(country.status || 'not_started').replaceAll('_', ' ')}
                  </div>
                  <div style={{ color: 'var(--text2)', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                    rows {Number(country.row_count || 0).toLocaleString()}
                  </div>
                  <div style={{ color: 'var(--text3)', fontSize: 12, lineHeight: 1.35 }}>
                    {country.explanation}
                  </div>
                  <button onClick={() => backfillCountry(country.country)} title={`Backfill ${country.country}`} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8, padding: '7px 9px', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <RotateCcw size={12} />
                    Backfill
                  </button>
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>
    </div>
  )
}
