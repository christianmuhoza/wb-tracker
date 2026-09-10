import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { getToken, setToken, apiGet } from './api.js';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import Login from './views/Login.jsx';
import Overview from './views/Overview.jsx';
import Notices from './views/Notices.jsx';
import Settings from './views/Settings.jsx';
import Bidders from './views/Bidders.jsx';
import Borrowers from './views/Borrowers.jsx';
import AwardAlerts from './views/AwardAlerts.jsx';
import SoftwareOpportunities from './views/SoftwareOpportunities.jsx';
import Operations from './views/Operations.jsx';
import { Globe, FileSearch, Activity, SlidersHorizontal, Bell, Building, Cpu, LogOut, Server } from 'lucide-react';

function ProtectedRoute({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return children;
}

function Sidebar({ username, onLogout }) {
  const navItems = [
    { to: '/', label: 'Overview', icon: Globe, end: true },
    { to: '/notices', label: 'Notices', icon: FileSearch },
    { to: '/software', label: 'Software Intelligence', icon: Cpu },
    { to: '/borrowers', label: 'Institutions', icon: Building },
    { to: '/bidders', label: 'Bidders', icon: Activity },
    { to: '/awards', label: 'Award Alerts', icon: Bell },
    { to: '/settings', label: 'Settings', icon: SlidersHorizontal },
    { to: '/operations', label: 'Operations', icon: Server },
  ];

  const linkStyle = ({ isActive }) => ({
    width: '100%', display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 14px', borderRadius: 8, border: 'none', textDecoration: 'none',
    background: isActive ? 'var(--surface2)' : 'transparent',
    color: isActive ? 'var(--accent)' : 'var(--text2)',
    fontFamily: 'var(--font-body)', fontSize: 14, fontWeight: isActive ? 500 : 400,
    marginBottom: 4, transition: 'all 0.15s',
    borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
  });

  return (
    <nav style={{
      width: 220, background: 'var(--surface)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', padding: 0, flexShrink: 0,
    }}>
      <div style={{ padding: '28px 24px 20px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          fontFamily: 'var(--font-head)', fontWeight: 800, fontSize: 18,
          color: 'var(--accent)', letterSpacing: '-0.5px', lineHeight: 1.1,
        }}>
          WB Procurement Tracker<br />
          <span style={{ color: 'var(--text2)', fontWeight: 400, fontSize: 12 }}>
            Africa Tracker
          </span>
        </div>
      </div>

      <div style={{ padding: '16px 12px', flex: 1 }}>
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} style={linkStyle}>
            <Icon size={16} />
            <span style={{ flex: 1, textAlign: 'left' }}>{label}</span>
          </NavLink>
        ))}
      </div>

      <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border)' }}>
        <div style={{
          fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)',
          marginBottom: 8,
        }}>
          Signed in as {username}
        </div>
        <button onClick={onLogout} style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border)',
          background: 'var(--surface2)', color: 'var(--text2)', fontSize: 12,
          cursor: 'pointer', fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}>
          <LogOut size={12} />
          Sign out
        </button>
      </div>
    </nav>
  );
}

function AppLayout() {
  const [username, setUsername] = useState(() => localStorage.getItem('wb-user') || 'admin');
  const navigate = useNavigate();

  const handleLogout = useCallback(() => {
    setToken(null);
    localStorage.removeItem('wb-user');
    navigate('/login');
  }, [navigate]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar username={username} onLogout={handleLogout} />
      <main style={{ flex: 1, overflow: 'auto', background: 'var(--bg)' }}>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/notices" element={<Notices />} />
            <Route path="/software" element={<SoftwareOpportunities />} />
            <Route path="/borrowers" element={<Borrowers />} />
            <Route path="/bidders" element={<Bidders />} />
            <Route path="/awards" element={<AwardAlerts />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/operations" element={<Operations />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      </main>
    </div>
  );
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(() => !!getToken());

  const handleLogin = useCallback((user) => {
    localStorage.setItem('wb-user', user);
    setLoggedIn(true);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={
          loggedIn ? <Navigate to="/" replace /> : <Login onLogin={handleLogin} />
        } />
        <Route path="/*" element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
}
