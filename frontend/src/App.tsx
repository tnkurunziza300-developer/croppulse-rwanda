import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Activity, BarChart3, ChevronDown, ClipboardCheck, CloudSun, FileSpreadsheet, HeartPulse, Leaf, Menu, MessageCircle, Settings, ShieldCheck, Users, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { AuthProvider, useAuth } from './auth';
import { LoginPage } from './LoginPage';
import { createStreamlitHandoff } from './api';
import type { Role } from './api';

const OverviewPage = lazy(() => import('./pages').then((module) => ({ default: module.OverviewPage })));
const FarmsPage = lazy(() => import('./pages').then((module) => ({ default: module.FarmsPage })));
const ReviewPage = lazy(() => import('./pages').then((module) => ({ default: module.ReviewPage })));
const AccountsPage = lazy(() => import('./pages').then((module) => ({ default: module.AccountsPage })));
const ReportsPage = lazy(() => import('./pages').then((module) => ({ default: module.ReportsPage })));
const SystemPage = lazy(() => import('./pages').then((module) => ({ default: module.SystemPage })));
const SettingsPage = lazy(() => import('./pages').then((module) => ({ default: module.SettingsPage })));
const MessagingPage = lazy(() => import('./MessagingPage').then((module) => ({ default: module.MessagingPage })));
const WeatherPage = lazy(() => import('./WeatherPage').then((module) => ({ default: module.WeatherPage })));
const CropHealthPage = lazy(() => import('./CropHealthPage').then((module) => ({ default: module.CropHealthPage })));
const CropHealthReviewPage = lazy(() => import('./CropHealthReviewPage').then((module) => ({ default: module.CropHealthReviewPage })));
const AgriculturalDataPage = lazy(() => import('./AgriculturalDataPage').then((module) => ({ default: module.AgriculturalDataPage })));

const nav: { to: string; label: string; icon: LucideIcon; roles: Role[] }[] = [
  { to: '/overview', label: 'Overview', icon: BarChart3, roles: ['farmer', 'reviewer', 'admin'] },
  { to: '/farms', label: 'My farms', icon: Leaf, roles: ['farmer'] },
  { to: '/review', label: 'Data review', icon: ClipboardCheck, roles: ['reviewer', 'admin'] },
  { to: '/messages', label: 'Private messages', icon: MessageCircle, roles: ['farmer', 'reviewer'] },
  { to: '/crop-health', label: 'Crop health reports', icon: HeartPulse, roles: ['farmer'] },
  { to: '/crop-health-review', label: 'Crop health review', icon: ClipboardCheck, roles: ['reviewer', 'admin'] },
  { to: '/weather', label: 'Weather & climate', icon: CloudSun, roles: ['farmer', 'reviewer', 'admin'] },
  { to: '/agricultural-data', label: 'National statistics', icon: BarChart3, roles: ['farmer', 'reviewer', 'admin'] },
  { to: '/accounts', label: 'Farmer accounts', icon: Users, roles: ['admin'] },
  { to: '/reports', label: 'Reports & exports', icon: FileSpreadsheet, roles: ['admin'] },
  { to: '/system', label: 'System health', icon: Activity, roles: ['admin'] },
  { to: '/settings', label: 'Settings', icon: Settings, roles: ['farmer', 'reviewer', 'admin'] },
] as const;

function ProtectedPage({ role, children }: { role: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/" replace />;
  if (!role.includes(user.role)) return <section className="state-card"><ShieldCheck /><h2>Access restricted</h2><p>Your account does not have permission to open this workspace.</p><Link to="/overview" className="button button-secondary">Return to overview</Link></section>;
  return children;
}

function Workspace() {
  const { user, ready, error, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [handoffError, setHandoffError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const returningToStreamlit = new URLSearchParams(location.search).get('cp_return') === 'streamlit';
  const startingStreamlitReturn = useRef(false);
  useEffect(() => {
    if (!user || !returningToStreamlit || startingStreamlitReturn.current) return;
    startingStreamlitReturn.current = true;
    setHandoffError('');
    navigate({ pathname: location.pathname || '/overview', search: '', hash: location.hash }, { replace: true });
    void createStreamlitHandoff().then((handoff) => {
      window.location.assign(handoff.redirect_url);
    }).catch((err: unknown) => {
      startingStreamlitReturn.current = false;
      setHandoffError(err instanceof Error ? `Signed in successfully, but the planning workspace could not be opened: ${err.message}` : 'Signed in successfully, but the planning workspace could not be opened.');
    });
  }, [user, returningToStreamlit, navigate, location.pathname, location.hash]);
  if (!ready) return <div className="launch-screen"><div className="brand-mark"><Leaf size={22} /></div><span>Opening your workspace…</span></div>;
  if (location.pathname === '/reset-password' || location.pathname === '/confirm-email-change') return <LoginPage serviceError="" />;
  if (!user) return <LoginPage serviceError={error} />;
  const current = nav.find((item) => item.to === location.pathname);
  const roleName = user.role === 'admin' ? 'Platform administrator' : user.role === 'reviewer' ? 'Agricultural reviewer' : 'Farmer account';

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Leaf size={21} strokeWidth={2.1} /></div><div><strong>CropPulse</strong><span>RWANDA · FIELD INTELLIGENCE</span></div><button className="icon-button mobile-only" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation" className="main-nav">{nav.filter((item) => item.roles.includes(user.role)).map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
      <div className="sidebar-bottom"><div className="secure-note"><ShieldCheck size={16} /><span>Private workspace<br /><small>Access is role controlled</small></span></div><div className="sidebar-version">CropPulse Rwanda <span>Phase 1</span></div></div>
    </aside>
    {sidebarOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-only" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={19} /></button><div className="crumb"><span>Workspace</span><b>/</b><strong>{current?.label ?? 'Overview'}</strong></div></div>
        <div className="account-menu-wrap"><button className="account-button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen}><span className="avatar">{user.display_name.slice(0, 1).toUpperCase()}</span><span className="account-meta"><strong>{user.display_name}</strong><small>{roleName}</small></span><ChevronDown size={15} /></button>
          {menuOpen && <div className="account-menu"><Link to="/settings" onClick={() => setMenuOpen(false)}>Account settings</Link><button onClick={() => { setMenuOpen(false); void logout(); }}>Sign out</button></div>}
        </div>
      </header>
      {error && <div className="notice notice-error session-notice" role="alert">{error}</div>}
      {handoffError && <div className="notice notice-error session-notice" role="alert">{handoffError}</div>}
      <div className="page-frame"><Suspense fallback={<div role="status" className="inline-state">Loading workspace…</div>}><Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/farms" element={<ProtectedPage role={['farmer']}><FarmsPage /></ProtectedPage>} />
        <Route path="/review" element={<ProtectedPage role={['reviewer', 'admin']}><ReviewPage /></ProtectedPage>} />
        <Route path="/messages" element={<ProtectedPage role={['farmer', 'reviewer']}><MessagingPage /></ProtectedPage>} />
        <Route path="/crop-health" element={<ProtectedPage role={['farmer']}><CropHealthPage /></ProtectedPage>} />
        <Route path="/crop-health-review" element={<ProtectedPage role={['reviewer', 'admin']}><CropHealthReviewPage /></ProtectedPage>} />
        <Route path="/weather" element={<WeatherPage />} />
        <Route path="/agricultural-data" element={<AgriculturalDataPage />} />
        <Route path="/accounts" element={<ProtectedPage role={['admin']}><AccountsPage /></ProtectedPage>} />
        <Route path="/reports" element={<ProtectedPage role={['admin']}><ReportsPage /></ProtectedPage>} />
        <Route path="/system" element={<ProtectedPage role={['admin']}><SystemPage /></ProtectedPage>} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes></Suspense></div>
    </main>
  </div>;
}

export function App() { return <AuthProvider><Workspace /></AuthProvider>; }
