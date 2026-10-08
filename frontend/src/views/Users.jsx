import { useMemo, useState } from 'react'
import { KeyRound, Mail, Plus, RefreshCw, ShieldCheck, Trash2, UserPlus, UserX } from 'lucide-react'
import { apiDelete, apiPost, apiPut } from '../api.js'
import { useApi } from '../hooks/useApi.js'

const ROLES = ['viewer', 'operator', 'admin']

const ROLE_COLORS = { viewer: '#8fa3c0', operator: '#3db2ff', admin: '#f0a500' }

const inputStyle = {
  width: '100%', background: 'var(--surface2)', color: 'var(--text)',
  border: '1px solid var(--border)', borderRadius: 8, padding: '9px 11px',
  fontSize: 13, fontFamily: 'var(--font-body)', boxSizing: 'border-box',
}

const labelStyle = {
  display: 'block', color: 'var(--text3)', fontSize: 10,
  fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
  letterSpacing: '0.06em', marginBottom: 6,
}

const buttonStyle = {
  display: 'inline-flex', alignItems: 'center', gap: 7, background: 'var(--accent)',
  color: '#0b1220', border: 'none', borderRadius: 8, padding: '9px 14px',
  fontSize: 13, fontWeight: 600, cursor: 'pointer',
}

const ghostButtonStyle = {
  display: 'inline-flex', alignItems: 'center', gap: 6, background: 'transparent',
  border: '1px solid var(--border)', color: 'var(--text2)', borderRadius: 8,
  padding: '8px 12px', fontSize: 12, cursor: 'pointer',
}

const iconButtonStyle = {
  background: 'transparent', border: '1px solid var(--border)', borderRadius: 6,
  padding: 6, cursor: 'pointer', display: 'inline-flex',
}

function RolePill({ role }) {
  const color = ROLE_COLORS[role] || 'var(--text2)'
  return (
    <span style={{
      display: 'inline-block', padding: '3px 9px', borderRadius: 999,
      border: `1px solid ${color}`, color, fontSize: 11,
      fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
    }}>{role}</span>
  )
}

export default function Users() {
  const [refreshKey, setRefreshKey] = useState(0)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState(null)
  const [resetLink, setResetLink] = useState('')
  const [form, setForm] = useState({ username: '', password: '', email: '', role: 'viewer' })
  const [editForm, setEditForm] = useState({ email: '', role: 'viewer', password: '' })

  const { data: users, loading } = useApi(`/auth/users?t=${refreshKey}`, [refreshKey])

  const refresh = () => setRefreshKey(key => key + 1)

  const flash = (text, isError = false) => {
    if (isError) { setError(text); setMessage('') } else { setMessage(text); setError('') }
    window.setTimeout(() => { setMessage(''); setError('') }, 6000)
  }

  const createUser = async (event) => {
    event.preventDefault()
    try {
      await apiPost('/auth/users', {
        username: form.username.trim(),
        password: form.password,
        email: form.email.trim() || null,
        role: form.role,
      })
      flash(`User "${form.username.trim()}" created.`)
      setForm({ username: '', password: '', email: '', role: 'viewer' })
      setShowCreate(false)
      refresh()
    } catch (e) {
      flash(`Could not create user: ${e.message}`, true)
    }
  }

  const startEdit = (user) => {
    setEditing(user.username)
    setEditForm({ email: user.email || '', role: user.role || 'viewer', password: '' })
    setResetLink('')
  }

  const saveEdit = async (username) => {
    const body = { email: editForm.email.trim() || null, role: editForm.role }
    if (editForm.password) body.password = editForm.password
    try {
      await apiPut(`/auth/users/${encodeURIComponent(username)}`, body)
      flash(`User "${username}" updated.`)
      setEditing(null)
      refresh()
    } catch (e) {
      flash(`Could not update user: ${e.message}`, true)
    }
  }

  const toggleActive = async (user) => {
    try {
      await apiPut(`/auth/users/${encodeURIComponent(user.username)}`, { is_active: !user.is_active })
      flash(`User "${user.username}" ${user.is_active ? 'deactivated' : 'reactivated'}.`)
      refresh()
    } catch (e) {
      flash(`Could not update user: ${e.message}`, true)
    }
  }

  const deleteUser = async (user) => {
    if (!window.confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
    try {
      await apiDelete(`/auth/users/${encodeURIComponent(user.username)}`)
      flash(`User "${user.username}" deleted.`)
      refresh()
    } catch (e) {
      flash(`Could not delete user: ${e.message}`, true)
    }
  }

  const sendResetLink = async (user) => {
    if (!user.email) {
      flash(`"${user.username}" has no email address — set one first, or copy the link instead.`, true)
      return
    }
    try {
      const data = await apiPost(`/auth/users/${encodeURIComponent(user.username)}/reset-token`, { send_email: true })
      setResetLink(data.reset_url)
      flash(`Reset link emailed to ${user.email}.`)
    } catch (e) {
      flash(`Could not send reset link: ${e.message}`, true)
    }
  }

  const copyResetLink = async (user) => {
    try {
      const data = await apiPost(`/auth/users/${encodeURIComponent(user.username)}/reset-token`, { send_email: false })
      setResetLink(data.reset_url)
      try {
        await navigator.clipboard.writeText(data.reset_url)
        flash(`Reset link for "${user.username}" copied to clipboard.`)
      } catch {
        flash(`Reset link for "${user.username}" generated below.`)
      }
    } catch (e) {
      flash(`Could not generate reset link: ${e.message}`, true)
    }
  }

  const counts = useMemo(() => {
    const list = users || []
    return {
      total: list.length,
      active: list.filter(u => u.is_active).length,
      admins: list.filter(u => u.role === 'admin').length,
      withEmail: list.filter(u => u.email).length,
    }
  }, [users])

  const thStyle = { textAlign: 'left', padding: '9px 12px', color: 'var(--text3)', fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }

  return (
    <div style={{ padding: 32, maxWidth: 1100 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 32, fontWeight: 800, letterSpacing: '-1px' }}>Users</h1>
          <p style={{ color: 'var(--text2)', marginTop: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
            Manage accounts, roles, and password resets.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={refresh} style={ghostButtonStyle} title="Refresh"><RefreshCw size={14} /></button>
          <button onClick={() => setShowCreate(v => !v)} style={buttonStyle}>
            <UserPlus size={14} /> New user
          </button>
        </div>
      </div>

      {message && <div style={{ marginBottom: 16, background: 'var(--surface2)', border: '1px solid var(--border)', color: '#00d4aa', borderRadius: 10, padding: '10px 12px', fontSize: 13 }}>{message}</div>}
      {error && <div style={{ marginBottom: 16, background: '#2a1518', border: '1px solid #7d3038', color: '#ff9999', borderRadius: 10, padding: '10px 12px', fontSize: 13 }}>{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 20 }}>
        {[
          ['Total users', counts.total],
          ['Active', counts.active],
          ['Admins', counts.admins],
          ['With email', counts.withEmail],
        ].map(([label, value]) => (
          <div key={label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
            <div style={{ color: 'var(--text3)', fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>{label}</div>
            <div style={{ marginTop: 6, fontSize: 24, fontWeight: 700 }}>{value ?? '--'}</div>
          </div>
        ))}
      </div>

      {showCreate && (
        <form onSubmit={createUser} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 20, marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-head)', fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Plus size={16} /> Create user
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
            <div>
              <label style={labelStyle}>Username *</label>
              <input required value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} style={inputStyle} autoComplete="off" />
            </div>
            <div>
              <label style={labelStyle}>Password * (min 8 chars)</label>
              <input required type="password" minLength={8} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} style={inputStyle} autoComplete="new-password" />
            </div>
            <div>
              <label style={labelStyle}>Email</label>
              <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} style={inputStyle} placeholder="needed for forgot-password" />
            </div>
            <div>
              <label style={labelStyle}>Role</label>
              <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} style={inputStyle}>
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button type="submit" style={buttonStyle}><Plus size={14} /> Create</button>
            <button type="button" onClick={() => setShowCreate(false)} style={ghostButtonStyle}>Cancel</button>
          </div>
        </form>
      )}

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 20 }}>
        <div style={{ fontFamily: 'var(--font-head)', fontWeight: 600, marginBottom: 14 }}>All users</div>
        {loading ? <div style={{ color: 'var(--text3)' }}>Loading users...</div> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
              <thead><tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Username', 'Email', 'Role', 'Status', 'Actions'].map(label => <th key={label} style={thStyle}>{label}</th>)}
              </tr></thead>
              <tbody>
                {(users || []).map(user => (
                  <UserRow
                    key={user.username}
                    user={user}
                    editing={editing === user.username}
                    editForm={editForm}
                    setEditForm={setEditForm}
                    onStartEdit={() => startEdit(user)}
                    onCancelEdit={() => setEditing(null)}
                    onSave={() => saveEdit(user.username)}
                    onToggle={() => toggleActive(user)}
                    onDelete={() => deleteUser(user)}
                    onSendReset={() => sendResetLink(user)}
                    onCopyReset={() => copyResetLink(user)}
                  />
                ))}
              </tbody>
            </table>
            {!users?.length && <div style={{ color: 'var(--text3)', padding: 16 }}>No users found.</div>}
          </div>
        )}
      </div>

      {resetLink && (
        <div style={{ marginTop: 16, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ color: 'var(--text3)', fontSize: 10, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', marginBottom: 8 }}>
            Password reset link (expires in 30 minutes)
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <input readOnly value={resetLink} style={{ ...inputStyle, fontFamily: 'var(--font-mono)', fontSize: 12 }} onFocus={e => e.target.select()} />
            <button
              onClick={() => { navigator.clipboard?.writeText(resetLink); flash('Reset link copied.') }}
              style={ghostButtonStyle}
            >Copy</button>
          </div>
        </div>
      )}

      <div style={{ marginTop: 18, color: 'var(--text3)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <ShieldCheck size={14} />
        Role changes apply on the user's next request. Password resets invalidate existing sessions.
      </div>
    </div>
  )
}

function UserRow({ user, editing, editForm, setEditForm, onStartEdit, onCancelEdit, onSave, onToggle, onDelete, onSendReset, onCopyReset }) {
  const tdStyle = { padding: '10px 12px', fontSize: 13, verticalAlign: 'middle' }
  const inputStyle2 = {
    width: '100%', background: 'var(--surface2)', color: 'var(--text)',
    border: '1px solid var(--border)', borderRadius: 6, padding: '6px 9px', fontSize: 13,
  }

  if (editing) {
    return (
      <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
        <td style={tdStyle}><span style={{ fontFamily: 'var(--font-mono)' }}>{user.username}</span></td>
        <td style={{ ...tdStyle, minWidth: 220 }}>
          <input type="email" value={editForm.email} placeholder="email address"
            onChange={e => setEditForm({ ...editForm, email: e.target.value })} style={inputStyle2} />
        </td>
        <td style={{ ...tdStyle, minWidth: 130 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <select value={editForm.role} onChange={e => setEditForm({ ...editForm, role: e.target.value })} style={inputStyle2}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <input type="password" value={editForm.password} placeholder="new password (optional)"
            onChange={e => setEditForm({ ...editForm, password: e.target.value })}
            style={{ ...inputStyle2, marginTop: 6 }} autoComplete="new-password" />
        </td>
        <td style={tdStyle}>
          <span style={{ color: user.is_active ? '#00d4aa' : '#ff6666', fontFamily: 'var(--font-mono)', fontSize: 11, textTransform: 'uppercase' }}>
            {user.is_active ? 'active' : 'disabled'}
          </span>
        </td>
        <td style={{ ...tdStyle, whiteSpace: 'nowrap' }}>
          <button onClick={onSave} title="Save" style={{ ...iconButtonStyle, color: '#00d4aa', marginRight: 6 }}>✓</button>
          <button onClick={onCancelEdit} title="Cancel" style={{ ...iconButtonStyle, color: 'var(--text3)' }}>✕</button>
        </td>
      </tr>
    )
  }

  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td style={tdStyle}>
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{user.username}</span>
        {!user.is_active && <span style={{ marginLeft: 8, color: '#ff6666', fontSize: 11, fontFamily: 'var(--font-mono)' }}>DISABLED</span>}
      </td>
      <td style={{ ...tdStyle, color: user.email ? 'var(--text2)' : 'var(--text3)' }}>
        {user.email || <span title="No email — forgot-password will not work">no email</span>}
      </td>
      <td style={tdStyle}><RolePill role={user.role} /></td>
      <td style={tdStyle}>
        <span style={{ color: user.is_active ? '#00d4aa' : '#ff6666', fontFamily: 'var(--font-mono)', fontSize: 11, textTransform: 'uppercase' }}>
          {user.is_active ? 'active' : 'disabled'}
        </span>
      </td>
      <td style={{ ...tdStyle, whiteSpace: 'nowrap' }}>
        <button onClick={onStartEdit} title="Edit user" style={{ ...iconButtonStyle, color: 'var(--accent)', marginRight: 6 }}><KeyRound size={13} /></button>
        <button onClick={onSendReset} title="Email reset link" style={{ ...iconButtonStyle, color: '#3db2ff', marginRight: 6 }}><Mail size={13} /></button>
        <button onClick={onCopyReset} title="Copy reset link"
          style={{ ...iconButtonStyle, color: 'var(--text2)', marginRight: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}>#</button>
        <button onClick={onToggle} title={user.is_active ? 'Deactivate' : 'Reactivate'} style={{ ...iconButtonStyle, color: '#f0a500', marginRight: 6 }}><UserX size={13} /></button>
        <button onClick={onDelete} title="Delete user" style={{ ...iconButtonStyle, color: '#ff6666' }}><Trash2 size={13} /></button>
      </td>
    </tr>
  )
}
