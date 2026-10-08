import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiPost } from '../api.js';
import { KeyRound } from 'lucide-react';

export default function ForgotPassword() {
  const [identifier, setIdentifier] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiPost('/auth/forgot-password', { identifier });
      setDone(true);
    } catch (err) {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
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
            Reset your password
          </div>
        </div>

        {done ? (
          <div style={{
            background: '#0d2b14', border: '1px solid #22c55e', color: '#4ade80',
            borderRadius: 8, padding: '14px 16px', fontSize: 13, marginBottom: 16,
            lineHeight: 1.5,
          }}>
            If an eligible account exists, a reset link will be sent to its email
            address when email delivery is enabled. Check your inbox.
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

            <div style={{ marginBottom: 8 }}>
              <label style={{
                fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
                textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6,
              }}>
                Username or email
              </label>
              <input
                type="text" value={identifier} onChange={e => setIdentifier(e.target.value)}
                autoFocus required
                style={{
                  width: '100%', background: 'var(--surface2)', border: '1px solid var(--border)',
                  color: 'var(--text)', borderRadius: 8, padding: '10px 14px', fontSize: 14, outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <p style={{
              color: 'var(--text3)', fontSize: 12, marginTop: 0, marginBottom: 24,
              lineHeight: 1.5,
            }}>
              Enter your username or the email on your account and we'll send
              you a link to choose a new password.
            </p>

            <button type="submit" disabled={loading} style={{
              width: '100%', background: 'var(--accent)', color: '#fff', border: 'none',
              borderRadius: 8, padding: '12px 0', fontSize: 14, fontWeight: 600,
              cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: 8, opacity: loading ? 0.7 : 1,
            }}>
              <KeyRound size={16} />
              {loading ? 'Sending...' : 'Send reset link'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Link to="/login" style={{
                color: 'var(--text2)', fontSize: 13, textDecoration: 'none',
              }}>
                Back to sign in
              </Link>
            </div>
          </form>
        )}

        {done && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Link to="/login" style={{
              color: 'var(--text2)', fontSize: 13, textDecoration: 'none',
            }}>
              Back to sign in
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
