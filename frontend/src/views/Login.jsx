import { useState } from 'react';
import { apiPost, setToken } from '../api.js';
import { LogIn } from 'lucide-react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await apiPost('/auth/login', { username, password });
      setToken(data.access_token);
      onLogin(data.username);
    } catch (err) {
      setError(err.message.includes('401') ? 'Invalid credentials' : 'Connection error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--bg)', fontFamily: 'var(--font-body)',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 16, padding: 40, width: 380, maxWidth: '90vw',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 20,
            color: 'var(--accent)', letterSpacing: '-0.5px',
          }}>
            WB Procurement Tracker
          </div>
          <div style={{ color: 'var(--text2)', fontSize: 13, marginTop: 4 }}>
            Sign in to continue
          </div>
        </div>

        {error && (
          <div style={{
            background: '#2b0d0d', border: '1px solid #ff4444', color: '#ff6666',
            borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16,
          }}>
            {error}
          </div>
        )}

        <div style={{ marginBottom: 16 }}>
          <label style={{
            fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6,
          }}>
            Username
          </label>
          <input
            type="text" value={username} onChange={e => setUsername(e.target.value)}
            autoFocus required
            style={{
              width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
              color: 'var(--text)', borderRadius: 8, padding: '10px 14px', fontSize: 14, outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{
            fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6,
          }}>
            Password
          </label>
          <input
            type="password" value={password} onChange={e => setPassword(e.target.value)}
            required
            style={{
              width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
              color: 'var(--text)', borderRadius: 8, padding: '10px 14px', fontSize: 14, outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>

        <button type="submit" disabled={loading} style={{
          width: '100%', background: 'var(--accent)', color: '#fff', border: 'none',
          borderRadius: 8, padding: '12px 0', fontSize: 14, fontWeight: 600,
          cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center',
          justifyContent: 'center', gap: 8, opacity: loading ? 0.7 : 1,
        }}>
          <LogIn size={16} />
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
