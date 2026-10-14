import { createContext, useContext, useEffect, useState, type FormEvent } from 'react';
import { createBrowserRouter, Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, CalendarDays, CheckCheck, ChevronRight, CircleHelp, ClipboardCheck, HeartPulse, LogOut, ShieldCheck, Sparkles } from 'lucide-react';
import { api, ApiError, errorMessage } from './api';
import { Brand, ErrorNotice, Modal, Spinner } from './components';
import type { Health, User } from './types';
import { Appointments } from './Appointments';
import { EncounterPage } from './Encounter';
import { TasksPage } from './Tasks';

type AuthContext = { user: User | null; health: Health | null; setUser: (user: User | null) => void };
const Auth = createContext<AuthContext>(null!);
export const useAuth = () => useContext(Auth);

function Root() {
  const [user, setUser] = useState<User | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [error, setError] = useState('');
  const [password, setPassword] = useState('');
  useEffect(() => {
    Promise.allSettled([api.me(), api.health()]).then(([identity, status]) => {
      if (identity.status === 'fulfilled') setUser(identity.value);
      if (status.status === 'fulfilled') setHealth(status.value);
      setLoading(false);
    });
    const expire = () => { setSessionExpired(true); setError(''); };
    window.addEventListener('clinicflow:session-expired', expire);
    return () => window.removeEventListener('clinicflow:session-expired', expire);
  }, []);
  async function restoreSession(e: FormEvent) {
    e.preventDefault(); setError('');
    try { const identity = await api.login(user!.email, password); setUser(identity); setPassword(''); setSessionExpired(false); }
    catch (err) { setError(errorMessage(err)); }
  }
  if (loading) return <div className="app-loading"><Brand /><Spinner label="Opening your workspace…" /></div>;
  return <Auth.Provider value={{ user, health, setUser }}><Outlet />{sessionExpired && user && <Modal title="Your session has expired" onClose={() => setSessionExpired(false)}><p>Your unsaved work is still in this tab. Sign in again to continue saving.</p><form onSubmit={restoreSession}><label>Email<input value={user.email} readOnly autoComplete="username" /></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" /></label>{error && <ErrorNotice message={error} />}<button className="button primary" type="submit">Restore session</button></form></Modal>}</Auth.Provider>;
}

function Login() {
  const { user, setUser, health } = useAuth();
  const [email, setEmail] = useState('doctor@clinicflow.demo');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  if (user) return <Navigate to={user.role === 'doctor' ? '/appointments' : '/tasks'} replace />;
  async function submit(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try { const result = await api.login(email, password); setUser(result); navigate(result.role === 'doctor' ? '/appointments' : '/tasks', { replace: true }); }
    catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  return <div className="login-layout"><section className="login-story"><Brand light /><div className="login-story-content"><span className="eyebrow">A LITTLE LESS ADMIN. A LITTLE MORE CARE.</span><h1>Good care deserves<br /><em>a clear next step.</em></h1><p>A thoughtful workspace for visit notes and follow-up. From the first conversation to the final checkmark.</p><div className="story-flow"><div><span><HeartPulse size={21} /></span>Listen</div><ChevronRight /><div><span><ClipboardCheck size={21} /></span>Review</div><ChevronRight /><div><span><CheckCheck size={21} /></span>Follow through</div></div></div><div className="story-footer"><ShieldCheck size={17} /> Fictional patients. Human-reviewed notes.</div></section><section className="login-form-area"><div className="login-mobile-brand"><Brand /></div><div className="login-form"><span className="eyebrow">YOUR CLINIC, CONNECTED</span><h2>Welcome back.</h2><p className="muted">Sign in to your care workspace.</p><div className="login-roles" aria-label="Choose demo role"><button type="button" className={email === 'doctor@clinicflow.demo' ? 'active' : ''} onClick={() => setEmail('doctor@clinicflow.demo')}>Doctor demo</button><button type="button" className={email === 'staff@clinicflow.demo' ? 'active' : ''} onClick={() => setEmail('staff@clinicflow.demo')}>Staff demo</button></div><form onSubmit={submit}><label>Email address<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label><label>Password<input type="password" autoComplete="current-password" placeholder="Enter your demo password" value={password} onChange={e => setPassword(e.target.value)} required /></label>{error && <ErrorNotice message={error} />}<button className="button primary login-submit" disabled={busy} type="submit">{busy ? 'Signing in…' : 'Open workspace'}<ArrowRight size={19} /></button></form><div className="login-note"><CircleHelp size={18} /><p>Use the password configured for this demo. All patient records are fictional.</p></div><div className="connection"><span className={health?.database === 'ok' ? 'connection-dot' : 'connection-dot offline'} />{health?.database === 'ok' ? 'Workspace connected' : 'Connection checked when you sign in'}</div></div><span className="login-footer">CLINICFLOW · PORTFOLIO DEMO</span></section></div>;
}

function Shell() {
  const { user, health } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showHelp, setShowHelp] = useState(false);
  if (!user) return <Navigate to="/login" replace />;
  const title = location.pathname.startsWith('/encounters') ? 'Encounter workspace' : location.pathname === '/tasks' ? 'Follow-up tasks' : 'Appointments';
  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to main content</a><aside className="sidebar"><Link to="/" className="brand-link" aria-label="ClinicFlow home"><Brand /></Link><div className="clinic-label"><span className="clinic-avatar">W</span><div>{user.clinic_name}<small>Dermatology practice</small></div></div><span className="nav-label">WORKSPACE</span><nav aria-label="Main navigation">{user.role === 'doctor' && <NavLink to="/appointments" className={({ isActive }) => isActive || location.pathname.startsWith('/encounters') ? 'nav-item active' : 'nav-item'}><CalendarDays size={20} />Appointments</NavLink>}<NavLink to="/tasks" className="nav-item"><ClipboardCheck size={20} />Follow-up tasks</NavLink></nav><div className="sidebar-bottom"><div className="review-note"><span className="review-note-icon"><ShieldCheck size={22} /></span><strong>Your review matters.</strong><p>Every draft stays a draft until a doctor approves it.</p></div><button type="button" className="nav-item help-button" onClick={() => setShowHelp(true)}><CircleHelp size={19} />Demo guide</button><div className="profile"><span className="avatar profile-avatar">{user.name.replace('Dr. ', '').split(' ').map(n => n[0]).join('').slice(0, 2)}</span><div><strong>{user.name}</strong><small>{user.role === 'doctor' ? 'Doctor' : 'Care coordinator'}</small></div><button type="button" className="icon-button" aria-label="Sign out" title="Sign out" onClick={() => navigate('/logout')}><LogOut size={18} /></button></div></div></aside><div className="app-body"><header className="topbar"><div className="breadcrumbs">Workspace<ChevronRight size={15} /><span>{title}</span></div><span className="workspace-status"><span className={health?.database === 'ok' ? 'connection-dot' : 'connection-dot offline'} />{health?.database === 'ok' ? 'All systems connected' : 'Connection unavailable'}</span></header><div className="demo-banner"><Sparkles size={16} /><span><strong>Fictional demo workspace.</strong> {health?.ai_mode === 'demo' ? 'Drafting uses deterministic examples, not live AI.' : health?.ai_mode === 'live' ? 'AI drafts require clinician review.' : 'AI drafting is not configured. Manual notes are available.'}</span></div><main id="main-content" tabIndex={-1}><Outlet /></main><footer className="app-footer"><span>Designed around the way you care.</span><span>Fictional data only · ClinicFlow</span></footer></div>{showHelp && <Modal title="A visit, from start to follow-up" onClose={() => setShowHelp(false)}><ol className="guide-list"><li><strong>Open an appointment.</strong> Review the fictional visit transcript.</li><li><strong>Create the note.</strong> Add facts manually or generate a draft. Save changes before generation.</li><li><strong>Review the source.</strong> Follow evidence links, correct facts, and acknowledge any historical evidence that needs review.</li><li><strong>Approve with care.</strong> Approval locks the note and creates the proposed tasks.</li><li><strong>Follow through.</strong> Staff can claim unassigned tasks and mark their own tasks complete.</li></ol><p className="muted">No diagnosis or treatment recommendation is generated. Missing details remain not documented. Demo reset instructions are in the project README.</p></Modal>}</div>;
}
function Home() { const { user } = useAuth(); return <Navigate to={user ? user.role === 'doctor' ? '/appointments' : '/tasks' : '/login'} replace />; }
function Logout() {
  const { setUser } = useAuth(); const [error, setError] = useState(''); const navigate = useNavigate();
  useEffect(() => { api.logout().then(() => { setUser(null); navigate('/login', { replace: true }); }).catch(err => { if (err instanceof ApiError && err.status === 401) { setUser(null); navigate('/login', { replace: true }); } else setError(errorMessage(err)); }); }, [navigate, setUser]);
  return error ? <div className="page"><ErrorNotice message={error}><Link to="/">Return to workspace</Link></ErrorNotice></div> : <Spinner label="Signing out…" />;
}
function NotFound() { return <div className="page"><h1>That page isn’t here.</h1><p>Head back to your workspace to continue.</p><Link to="/" className="button primary">Open workspace</Link></div>; }
export const router = createBrowserRouter([{ element: <Root />, children: [{ path: '/login', element: <Login /> }, { path: '/', element: <Home /> }, { element: <Shell />, children: [{ path: '/appointments', element: <Appointments /> }, { path: '/encounters/:id', element: <EncounterPage /> }, { path: '/tasks', element: <TasksPage /> }, { path: '/logout', element: <Logout /> }, { path: '*', element: <NotFound /> }] }] }]);
