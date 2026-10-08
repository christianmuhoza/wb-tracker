import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { apiGet, apiPost } from '../api.js';
import { Lock, CheckCircle2 } from 'lucide-react';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [tokenStatus, setTokenStatus] = useState(token ? 'checking' : 'missing');

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiGet('/auth/reset-password/verify', { token })
      .then(() => { if (active) setTokenStatus('valid'); })
      .catch(() => { if (active) setTokenStatus('invalid'); });
    return () => { active = false; };
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setLoading(true);
    try {
      await apiPost('/auth/reset-password', { token, new_password: password });
      setDone(true);
    } catch (err) {
      if (err.message.includes('400')) {
        setError('Invalid or expired reset link. Request a new one.');
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
    color: 'var(--text)', borderRadius: 8, padding: '10px 14px', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
  };
  const labelStyle = {
    fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
    textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6,
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: 'var(--bg)', fontFamily: 'var(--font-body)',
    }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 16, padding: 40, width: 380, maxWidth: '90vw',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{
            fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 20,
            color: 'var(--accent)', letterSpacing: '-0.5px',
          }}>
            WB Procurement Tracker
          </div>
          <div style={{ color: 'var(--text2)', fontSize: 13, marginTop: 4 }}>
            Choose a new password
          </div>
        </div>

        {done ? (
          <div style={{ textAlign: 'center' }}>
            <CheckCircle2 size={40} color="var(--accent)" style={{ marginBottom: 12 }} />
            <div style={{
              background: '#0d2b14', border: '1px solid #22c55e', color: '#4ade80',
              borderRadius: 8, padding: '14px 16px', fontSize: 13, marginBottom: 20,
              lineHeight: 1.5,
            }}>
              Password has been reset. You can now sign in with your new password.
            </div>
            <Link to="/login" style={{
              background: 'var(--accent)', color: '#fff', textDecoration: 'none',
              borderRadius: 8, padding: '12px 0', fontSize: 14, fontWeight: 600,
              display: 'block', width: '100%',
            }}>
              Go to sign in
            </Link>
          </div>
        ) : !token ? (
          <div style={{
            background: '#2b0d0d', border: '1px solid #ff4444', color: '#ff6666',
            borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16,
          }}>
            This reset link is missing its token. Use the link from the email,
            or request a new one.
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Link to="/forgot-password" style={{ color: 'var(--text2)', fontSize: 13 }}>
                Request a new reset link
              </Link>
            </div>
          </div>
        ) : tokenStatus === 'checking' ? (
          <div style={{ color: 'var(--text2)', textAlign: 'center', fontSize: 13 }}>
            Checking reset link…
          </div>
        ) : tokenStatus === 'invalid' ? (
          <div style={{
            background: '#2b0d0d', border: '1px solid #ff4444', color: '#ff6666',
            borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16,
          }}>
            This reset link is invalid, expired, or already used.{' '}
            <Link to="/forgot-password" style={{ color: 'var(--text2)' }}>
              Request a new one
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && (
              <div style={{
                background: '#2b0d0d', border: '1px solid #ff4444', color: '#ff6666',
                borderRadius: 8, padding: '10px 14px', fontSize: 13, marginBottom: 16,
              }}>
                {error}
              </div>
            )}

            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>New password</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)}
                required autoFocus
                style={inputStyle}
              />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle}>Confirm new password</label>
              <input
                type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                required
                style={inputStyle}
              />
            </div>

            <button type="submit" disabled={loading} style={{
              width: '100%', background: 'var(--accent)', color: '#fff', border: 'none',
              borderRadius: 8, padding: '12px 0', fontSize: 14, fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 8, opacity: loading ? 0.7 : 1,
            }}>
              <Lock size={16} />
              {loading ? 'Resetting...' : 'Reset password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
