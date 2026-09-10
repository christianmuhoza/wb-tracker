import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Ban, CheckCircle, Clock3, RefreshCw, RotateCcw, Server, Timer } from 'lucide-react'
import { apiPost } from '../api.js'
import { useApi } from '../hooks/useApi.js'

const STATUS_COLORS = {
  queued: '#f0a500',
  running: '#3db2ff',
  completed: '#00d4aa',
  failed: '#ff6666',
  cancelled: '#8fa3c0',
}

function Metric({ label, value, icon: Icon, color }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderTop: `2px solid ${color}`, borderRadius: 'var(--radius-lg)', padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text3)', fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
        <Icon size={14} color={color} /> {label}
      </div>
      <div style={{ marginTop: 8, fontSize: 28, fontWeight: 700 }}>{value ?? 0}</div>
    </div>
  )
}

export default function Operations() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [status, setStatus] = useState('')
  const [message, setMessage] = useState('')
  const [selectedJob, setSelectedJob] = useState(null)
  const { data: summary, loading: summaryLoading } = useApi(`/api/operations/jobs/summary?t=${refreshKey}`, [refreshKey])
  const { data: jobs, loading: jobsLoading } = useApi(`/api/operations/jobs?t=${refreshKey}`, [refreshKey])

  useEffect(() => {
    const interval = window.setInterval(() => setRefreshKey(key => key + 1), 5000)
    return () => window.clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!selectedJob || !jobs) return
    const refreshed = jobs.find(job => job.id === selectedJob.id)
    if (refreshed) setSelectedJob(refreshed)
  }, [jobs, selectedJob?.id])

  const visibleJobs = useMemo(() => {
    if (!status) return jobs || []
    return (jobs || []).filter(job => job.status === status)
  }, [jobs, status])

  const runAction = async (jobId, action) => {
    try {
      await apiPost(`/operations/jobs/${jobId}/${action}`)
      setMessage(`Job #${jobId} ${action === 'retry' ? 'queued for retry' : 'cancelled'}.`)
      setRefreshKey(key => key + 1)
    } catch (error) {
      setMessage(`Could not ${action} job #${jobId}: ${error.message}`)
    }
  }

  const counts = summary?.counts || {}
  const progress = selectedJob?.progress_data || {}
  const heartbeatAge = selectedJob?.heartbeat_at
    ? Math.max(0, Math.round((Date.now() - new Date(selectedJob.heartbeat_at).getTime()) / 1000))
    : null
  const health = selectedJob?.status !== 'running'
    ? selectedJob?.status
    : heartbeatAge === null || heartbeatAge < 90 ? 'active' : heartbeatAge < 300 ? 'delayed' : 'stale'
  return (
    <div style={{ padding: 32, maxWidth: 1280 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 28 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 32, fontWeight: 800, letterSpacing: '-1px' }}>Operations</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Monitor ingestion jobs, retries, and worker health.
          </p>
        </div>
        <button onClick={() => setRefreshKey(key => key + 1)} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', borderRadius: 8, padding: 9 }}>
          <RefreshCw size={14} />
        </button>
      </div>

      {message && <div style={{ marginBottom: 18, background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 10, padding: '10px 12px', fontSize: 13 }}>{message}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 12, marginBottom: 20 }}>
        <Metric label="Queued" value={summaryLoading ? '--' : counts.queued} icon={Clock3} color={STATUS_COLORS.queued} />
        <Metric label="Running" value={summaryLoading ? '--' : counts.running} icon={Timer} color={STATUS_COLORS.running} />
        <Metric label="Completed" value={summaryLoading ? '--' : counts.completed} icon={CheckCircle} color={STATUS_COLORS.completed} />
        <Metric label="Failed" value={summaryLoading ? '--' : counts.failed} icon={AlertTriangle} color={STATUS_COLORS.failed} />
        <Metric label="Retry waiting" value={summaryLoading ? '--' : summary?.retry_waiting} icon={RotateCcw} color={STATUS_COLORS.queued} />
      </div>

      {summary?.stale_running > 0 && (
        <div style={{ marginBottom: 20, padding: 12, borderRadius: 10, border: '1px solid #7d4f26', background: '#2a1d12', color: '#ffc078', fontSize: 13 }}>
          {summary.stale_running} running job(s) have exceeded the six-hour lease and will be recovered by the worker.
        </div>
      )}

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <div style={{ fontFamily: 'var(--font-head)', fontWeight: 600 }}>Recent jobs</div>
          <select value={status} onChange={event => setStatus(event.target.value)} style={{ background: 'var(--surface2)', color: 'var(--text)', border: '1px solid var(--border)', borderRadius: 7, padding: '7px 10px' }}>
            <option value="">All statuses</option>
            {Object.keys(STATUS_COLORS).map(value => <option key={value} value={value}>{value}</option>)}
          </select>
        </div>
        {jobsLoading ? <div style={{ color: 'var(--text3)' }}>Loading jobs...</div> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
              <thead><tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Job', 'Type', 'Status', 'Attempts', 'Created', 'Next attempt', 'Error', 'Actions'].map(label => <th key={label} style={{ textAlign: 'left', padding: '8px 10px', color: 'var(--text3)', fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>{label}</th>)}
              </tr></thead>
              <tbody>{visibleJobs.map(job => (
                <tr key={job.id} onClick={() => setSelectedJob(job)} style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', background: selectedJob?.id === job.id ? 'var(--surface2)' : 'transparent' }}>
                  <td style={{ padding: '10px', fontFamily: 'var(--font-mono)' }}>#{job.id}</td>
                  <td style={{ padding: '10px' }}>{job.job_type}</td>
                  <td style={{ padding: '10px', color: STATUS_COLORS[job.status] || 'var(--text2)', fontWeight: 700 }}>{job.status}</td>
                  <td style={{ padding: '10px', fontFamily: 'var(--font-mono)' }}>{job.attempt_count || 0}/{job.max_attempts || 0}</td>
                  <td style={{ padding: '10px', color: 'var(--text3)', fontSize: 11 }}>{job.created_at || '--'}</td>
                  <td style={{ padding: '10px', color: 'var(--text3)', fontSize: 11 }}>{job.next_attempt_at || '--'}</td>
                  <td style={{ padding: '10px', color: '#ff9999', maxWidth: 260, fontSize: 11 }}>{job.error || '--'}</td>
                  <td style={{ padding: '10px', whiteSpace: 'nowrap' }}>
                    {['failed', 'cancelled'].includes(job.status) && <button onClick={() => runAction(job.id, 'retry')} title="Retry" style={{ marginRight: 6, background: 'transparent', border: '1px solid var(--border)', color: 'var(--accent)', borderRadius: 6, padding: 6 }}><RotateCcw size={13} /></button>}
                    {['queued', 'running'].includes(job.status) && <button onClick={() => runAction(job.id, 'cancel')} title="Cancel" style={{ background: 'transparent', border: '1px solid var(--border)', color: '#ff7777', borderRadius: 6, padding: 6 }}><Ban size={13} /></button>}
                  </td>
                </tr>
              ))}</tbody>
            </table>
            {!visibleJobs.length && <div style={{ color: 'var(--text3)', padding: 16 }}>No jobs match this filter.</div>}
          </div>
        )}
      </div>

      {selectedJob && (
        <div style={{ marginTop: 20, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ fontFamily: 'var(--font-head)', fontWeight: 600 }}>Job #{selectedJob.id} progress</div>
            <span style={{ color: health === 'active' || health === 'completed' ? '#00d4aa' : health === 'delayed' ? '#f0a500' : '#ff6666', fontFamily: 'var(--font-mono)', fontSize: 11, textTransform: 'uppercase' }}>
              {health}
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, color: 'var(--text2)', fontSize: 12 }}>
            <div><strong>Stage</strong><br />{progress.stage || selectedJob.status}</div>
            <div><strong>Current country</strong><br />{progress.current_country || '--'}</div>
            <div><strong>Page offset</strong><br />{progress.page_offset ?? '--'} {progress.page_size ? `(size ${progress.page_size})` : ''}</div>
            <div><strong>Records</strong><br />{progress.records_upserted ?? 0} upserted / {progress.records_new ?? 0} new</div>
          </div>
          <div style={{ marginTop: 16, color: 'var(--text3)', fontSize: 12 }}>
            {progress.message || selectedJob.progress || '--'}
            <span style={{ float: 'right', fontFamily: 'var(--font-mono)' }}>
              heartbeat {heartbeatAge === null ? '--' : `${heartbeatAge}s ago`}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
