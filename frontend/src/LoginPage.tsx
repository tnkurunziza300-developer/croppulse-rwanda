import { useState, type FormEvent } from 'react';
import { ArrowRight, Leaf, ShieldCheck } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { completePasswordReset, confirmEmailChange, requestPasswordRecovery } from './api';
import { useAuth } from './auth';

type AuthMode = 'login' | 'register' | 'recovery' | 'reset' | 'confirm-email-change';

export function LoginPage({ serviceError }: { serviceError: string }) {
  const { login, register, clearLocalSession } = useAuth();
  const location = useLocation();
  const [mode, setMode] = useState<AuthMode>(() => location.pathname === '/reset-password' ? 'reset' : location.pathname === '/confirm-email-change' ? 'confirm-email-change' : 'login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [name, setName] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);
  const actionToken = new URLSearchParams(location.search).get('token') ?? '';

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(''); setSuccess('');
    if (mode === 'register' && !accepted) { setError('Please accept the account data notice to continue.'); return; }
    if (mode === 'reset' && password !== confirmPassword) { setError('The passwords do not match.'); return; }
    setBusy(true);
    try {
      if (mode === 'register') await register(email.trim(), password, name.trim(), accepted);
      else if (mode === 'login') await login(email.trim(), password);
      else if (mode === 'recovery') {
        const result = await requestPasswordRecovery(email.trim()); setSuccess(result.message);
      } else if (mode === 'reset') {
        if (!actionToken) throw new Error('This password reset link is missing its token. Request a new link.');
        const result = await completePasswordReset(actionToken, password);
        clearLocalSession(); setSuccess(result.message); setMode('login'); setPassword(''); setConfirmPassword('');
      } else {
        if (!actionToken) throw new Error('This email confirmation link is missing its token. Request a new change.');
        const result = await confirmEmailChange(actionToken);
        clearLocalSession(); setSuccess(result.message); setMode('login');
      }
    } catch (err) { setError(err instanceof Error ? err.message : 'The account request could not be completed.'); }
    finally { setBusy(false); }
  }

  const heading = mode === 'login' ? 'Welcome back' : mode === 'register' ? 'Create your account' : mode === 'recovery' ? 'Reset your password' : mode === 'reset' ? 'Choose a new password' : 'Confirm your new email';
  const description = mode === 'login' ? 'Sign in to continue to your workspace.' : mode === 'register' ? 'Start saving farm records to your private account.' : mode === 'recovery' ? 'Enter your account email and we will send a one-time reset link.' : mode === 'reset' ? 'Choose a new password for your CropPulse account.' : 'Confirm that you own the new email address.';

  return <div className="auth-screen">
    <section className="auth-story"><div className="brand brand-on-dark"><div className="brand-mark"><Leaf size={21} /></div><div><strong>CropPulse</strong><span>RWANDA · FIELD INTELLIGENCE</span></div></div>
      <div className="story-copy"><span className="eyebrow eyebrow-light">AGRICULTURE, WITH BETTER EVIDENCE</span><h1>Clear insight for<br /><em>every growing season.</em></h1><p>One secure workspace for Rwanda’s farmers, agricultural reviewers, and platform team.</p><div className="story-foot"><ShieldCheck size={16} /><span>Farmer records are private to their account.</span></div></div>
      <div className="auth-landscape" aria-hidden="true"><span /><span /><span /><span /><span /><span /></div>
    </section>
    <section className="auth-panel"><div className="auth-card"><span className="eyebrow">CROP PULSE RWANDA</span><h2>{heading}</h2><p className="muted">{description}</p>
      {serviceError && <div className="notice notice-error" role="alert">{serviceError}</div>}
      {error && <div className="notice notice-error" role="alert">{error}</div>}
      {success && <div className="notice notice-success" role="status">{success}</div>}
      <form onSubmit={(event) => void submit(event)} className="form-stack">
        {mode === 'register' && <label>Your name<input autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} /></label>}
        {(mode === 'login' || mode === 'register' || mode === 'recovery') && <label>Email address<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={254} /></label>}
        {(mode === 'login' || mode === 'register' || mode === 'reset') && <label>{mode === 'reset' ? 'New password' : 'Password'}<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === 'register' || mode === 'reset' ? 12 : 1} maxLength={128} />{(mode === 'register' || mode === 'reset') && <small>Use at least 12 characters.</small>}</label>}
        {mode === 'reset' && <label>Confirm new password<input type="password" autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required minLength={12} maxLength={128} /></label>}
        {mode === 'register' && <label className="check-label"><input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} /><span>I have read and accept the <a href="/privacy-notice.html" target="_blank" rel="noreferrer">account data notice</a>.</span></label>}
        {mode === 'confirm-email-change' && <p className="notice notice-info">This confirmation link expires after 30 minutes and can be used once.</p>}
        <button className="button button-primary auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : mode === 'register' ? 'Create account' : mode === 'recovery' ? 'Send reset link' : mode === 'reset' ? 'Save new password' : 'Confirm email change'}<ArrowRight size={17} /></button>
      </form>
      <div className="auth-switch">{mode === 'login' ? <>New to CropPulse? <button type="button" onClick={() => { setMode('register'); setError(''); setSuccess(''); }}>Create account</button><button type="button" onClick={() => { setMode('recovery'); setError(''); setSuccess(''); }}>Forgot password?</button></> : mode === 'register' ? <>Already have an account? <button type="button" onClick={() => { setMode('login'); setError(''); setSuccess(''); }}>Sign in</button></> : <button type="button" onClick={() => { setMode('login'); setError(''); setSuccess(''); }}>Return to sign in</button>}</div>
      <div className="auth-note"><ShieldCheck size={15} /><span>Secure, role-based access. No passwords are stored in this browser.</span></div>
    </div></section>
  </div>;
}
