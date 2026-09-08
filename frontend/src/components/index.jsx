export function Badge({ type, colors }) {
  const defaults = {
    IFB: { bg: 'rgba(53,208,127,0.12)', color: '#00d4aa' },
    REOI: { bg: 'rgba(124,111,255,0.12)', color: '#7c6fff' },
    'Contract Award': { bg: 'rgba(167,243,194,0.16)', color: '#a7f3c2' },
    Award: { bg: 'rgba(167,243,194,0.16)', color: '#a7f3c2' },
  };
  const c = (colors || defaults)[type] || { bg: 'rgba(255,255,255,0.06)', color: '#aaa' };

  return (
    <span style={{
      background: c.bg, color: c.color, border: `1px solid ${c.color}33`,
      borderRadius: 999, padding: '2px 8px', fontSize: 11,
      fontWeight: 600, whiteSpace: 'nowrap',
    }}>
      {type || '-'}
    </span>
  );
}

export function StatusBadge({ status }) {
  const colors = {
    Active: { bg: '#0d2b1e', text: '#00d4aa', border: '#00d4aa' },
    Awarded: { bg: '#1a1a2e', text: '#7c6fff', border: '#7c6fff' },
    Cancelled: { bg: '#2b0d0d', text: '#ff6666', border: '#ff4444' },
    Closed: { bg: '#1a1a1a', text: '#8fa3c0', border: '#3a4a5c' },
    Pending: { bg: '#1a1500', text: '#f0a500', border: '#f0a500' },
    Published: { bg: '#1a2235', text: '#8fa3c0', border: '#3a4a5c' },
  };
  const c = colors[status] || { bg: '#1a2235', text: '#8fa3c0', border: '#3a4a5c' };

  return (
    <span style={{
      fontSize: 10, fontFamily: 'var(--font-mono)', padding: '2px 7px', borderRadius: 4,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
      fontWeight: 600, letterSpacing: '0.05em', whiteSpace: 'nowrap',
    }}>
      {status || '--'}
    </span>
  );
}

export function StatPill({ label, value, accent }) {
  return (
    <div style={{
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '10px 16px', minWidth: 110,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: accent || 'var(--text)' }}>{value}</div>
    </div>
  );
}

export function Section({ title, children }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: 24,
    }}>
      <div style={{
        fontFamily: 'var(--font-head)', fontSize: 14, fontWeight: 600,
        color: 'var(--text2)', marginBottom: 20, textTransform: 'uppercase',
        letterSpacing: '0.08em',
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export function InfoField({ label, value, isEmail = false, color }) {
  return (
    <div>
      <div style={{
        fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
        textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4,
      }}>
        {label}
      </div>
      <div style={{ fontSize: 13, color: color || 'inherit' }}>
        {isEmail && value
          ? <a href={`mailto:${value}`} style={{ color: 'var(--accent)' }}>{value}</a>
          : value || '--'}
      </div>
    </div>
  );
}

export function FilterSelect({ label, value, onChange, options }) {
  const isObj = typeof options[0] === 'object';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{
        fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
        textTransform: 'uppercase', letterSpacing: '0.06em',
      }}>
        {label}
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: 'var(--surface2)', border: '1px solid var(--border)',
          color: 'var(--text)', borderRadius: 8, padding: '7px 10px',
          fontSize: 13, outline: 'none', cursor: 'pointer',
        }}
      >
        <option value="">All</option>
        {options.map(o => {
          const v = isObj ? o.value : o;
          const l = isObj ? o.label : o;
          return <option key={v} value={v}>{l}</option>;
        })}
      </select>
    </div>
  );
}

export function FilterTag({ label, onRemove }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 20, padding: '3px 10px 3px 12px', fontSize: 11,
      color: 'var(--text2)', fontFamily: 'var(--font-mono)',
    }}>
      {label}
      <button
        onClick={onRemove}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text3)', display: 'flex', padding: 0 }}
      >
        ×
      </button>
    </div>
  );
}
