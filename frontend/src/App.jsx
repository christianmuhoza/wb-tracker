import { useEffect, useState } from 'react'
import Overview from './views/Overview.jsx'
import Notices from './views/Notices.jsx'
import Settings from './views/Settings.jsx'
import Bidders from './views/Bidders.jsx'
import Borrowers from './views/Borrowers.jsx'
import AwardAlerts from './views/AwardAlerts.jsx'
import SoftwareOpportunities from './views/SoftwareOpportunities.jsx'

import { Globe, FileSearch, Activity, SlidersHorizontal, Bell, Building, Cpu } from 'lucide-react'

export default function App() {
  const [view, setView] = useState('overview')
  const [awardUnread, setAwardUnread] = useState(0)
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    return window.localStorage.getItem('wb-theme') || 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('wb-theme', theme)
  }, [theme])
  useEffect(() => {
    let active = true
    const loadAwardCount = async () => {
      try {
        const res = await fetch('/api/award-alerts?page_size=1')
        if (!res.ok) return
        const data = await res.json()
        if (active) setAwardUnread(data.unread || 0)
      } catch {
        if (active) setAwardUnread(0)
      }
    }
    loadAwardCount()
    const interval = setInterval(loadAwardCount, 60000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [view])

  const navItems = [
    { id: 'overview', label: 'Overview', icon: Globe },
    { id: 'notices', label: 'Notices', icon: FileSearch },
    { id: 'software', label: 'Software Intelligence', icon: Cpu },
    { id: 'borrowers', label: 'Institutions', icon: Building },
    { id: 'bidders', label: 'Bidders', icon: Activity },
    { id: 'awards', label: 'Award Alerts', icon: Bell, badge: awardUnread },
    { id: 'settings', label: 'Settings', icon: SlidersHorizontal },
  ]

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <nav style={{
        width: 220, background: 'var(--surface)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', padding: '0', flexShrink: 0
      }}>
        <div style={{ padding: '28px 24px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{
            fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 18,
            color: 'var(--accent)', letterSpacing: '-0.5px', lineHeight: 1.1
          }}>
            WB Procurement Tracker<br />
            <span style={{ color: 'var(--text2)', fontWeight: 400, fontSize: 12 }}>
              Africa Tracker
            </span>
          </div>
          <button
            onClick={() => setTheme(current => current === 'dark' ? 'light' : 'dark')}
            style={{
              marginTop: 16,
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid var(--border)',
              background: 'var(--surface2)',
              color: 'var(--text)',
              fontSize: 12,
              fontFamily: 'var(--font-mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            <span>Theme</span>
            <span>{theme === 'dark' ? 'Dark' : 'Light'}</span>
          </button>
        </div>

        <div style={{ padding: '16px 12px', flex: 1 }}>
          {navItems.map(({ id, label, icon: Icon, badge }) => (
            <button
              key={id}
              onClick={() => setView(id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 14px', borderRadius: 8, border: 'none',
                background: view === id ? 'var(--surface2)' : 'transparent',
                color: view === id ? 'var(--accent)' : 'var(--text2)',
                fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: view === id ? 500 : 400,
                marginBottom: 4, transition: 'all 0.15s',
                borderLeft: view === id ? '2px solid var(--accent)' : '2px solid transparent',
              }}
            >
              <Icon size={16} />
              <span style={{ flex: 1, textAlign: 'left' }}>{label}</span>
              {badge > 0 && (
                <span style={{ minWidth: 20, height: 20, borderRadius: 999, background: 'var(--accent)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{badge > 99 ? '99+' : badge}</span>
              )}
            </button>
          ))}
        </div>

        <div style={{
          padding: '16px 24px', borderTop: '1px solid var(--border)',
          fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Activity size={10} color="var(--accent)" />
            Auto-sync daily
          </div>
          <div style={{ marginTop: 4 }}>Coverage updates with each fetch</div>
        </div>
      </nav>

      <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg)' }}>
        {view === 'overview' && <Overview />}
        {view === 'notices' && <Notices />}
        {view === 'software' && <SoftwareOpportunities />}
        {view === 'borrowers' && <Borrowers />}
        {view === 'bidders' && <Bidders />}
        {view === 'awards' && <AwardAlerts />}
        {view === 'settings' && <Settings />}
      </main>
    </div>
  )
}
