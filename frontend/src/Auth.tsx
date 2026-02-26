import { useState } from 'react';
import { Mail, Lock, KeyRound, ChevronRight, AlertCircle, Loader2 } from 'lucide-react';
import { api, setAuthToken } from './api';

export function AuthScreen({ onAuthSuccess }: { onAuthSuccess: () => void }) {
    const [mode, setMode] = useState<'login' | 'signup' | 'verify'>('login');

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [code, setCode] = useState('');

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setLoading(true);

        try {
            if (mode === 'signup') {
                const res = await api.signup(email, password);
                if (res.success) {
                    setMessage(res.message || 'Account created! Please check your email for the verification code.');
                    setMode('verify');
                } else {
                    setError(res.error || 'Signup failed');
                }
            } else if (mode === 'verify') {
                const res = await api.verify(email, code);
                if (res.success && res.token) {
                    setAuthToken(res.token);
                    onAuthSuccess();
                } else {
                    setError(res.error || 'Verification failed');
                }
            } else {
                const res = await api.login(email, password);
                if (res.success && res.token) {
                    setAuthToken(res.token);
                    onAuthSuccess();
                } else {
                    setError(res.error || 'Login failed');
                }
            }
        } catch (err: any) {
            setError(err.message || 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: 'var(--color-bg)' }}>
            <div
                className="w-full max-w-md p-8 rounded-2xl border flex flex-col items-center"
                style={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: '0 20px 40px -10px rgba(0,0,0,0.5)' }}
            >
                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-6" style={{ background: 'var(--color-blue-glow)', color: 'var(--color-blue)' }}>
                    <Lock size={32} />
                </div>

                <h1 className="text-2xl font-semibold text-white mb-2">
                    {mode === 'login' ? 'Welcome Back' : mode === 'signup' ? 'Create an Account' : 'Verify Email'}
                </h1>
                <p className="text-sm mb-8 text-center" style={{ color: 'var(--color-muted)' }}>
                    {mode === 'login' ? 'Sign in to access Vanguard.' : mode === 'signup' ? 'Sign up to start tracking queries.' : 'Enter the code sent to your email.'}
                </p>

                {error && (
                    <div className="w-full p-3 mb-6 rounded-lg text-sm flex items-center gap-2 border" style={{ backgroundColor: 'rgba(248, 113, 113, 0.1)', color: 'var(--color-red)', borderColor: 'rgba(248, 113, 113, 0.2)' }}>
                        <AlertCircle size={16} />
                        {error}
                    </div>
                )}

                {message && (
                    <div className="w-full p-3 mb-6 rounded-lg text-sm flex items-center gap-2 border" style={{ backgroundColor: 'rgba(52, 211, 153, 0.1)', color: 'var(--color-green)', borderColor: 'rgba(52, 211, 153, 0.2)' }}>
                        <CheckCircle2 size={16} className="text-emerald-400" />
                        {message}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium" style={{ color: 'var(--color-muted)' }}>Email Address</label>
                        <div className="relative flex items-center">
                            <Mail size={16} className="absolute left-3" style={{ color: 'var(--color-muted)' }} />
                            <input
                                type="email"
                                required
                                disabled={mode === 'verify'}
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                className="w-full h-11 pl-10 pr-4 rounded-lg bg-transparent border focus:outline-none transition-colors"
                                style={{ borderColor: 'var(--color-border)', color: 'white' }}
                                placeholder="you@example.com"
                            />
                        </div>
                    </div>

                    {mode !== 'verify' && (
                        <div className="flex flex-col gap-1">
                            <label className="text-xs font-medium" style={{ color: 'var(--color-muted)' }}>Password</label>
                            <div className="relative flex items-center">
                                <KeyRound size={16} className="absolute left-3" style={{ color: 'var(--color-muted)' }} />
                                <input
                                    type="password"
                                    required
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="w-full h-11 pl-10 pr-4 rounded-lg bg-transparent border focus:outline-none transition-colors"
                                    style={{ borderColor: 'var(--color-border)', color: 'white' }}
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>
                    )}

                    {mode === 'verify' && (
                        <div className="flex flex-col gap-1">
                            <label className="text-xs font-medium" style={{ color: 'var(--color-muted)' }}>Verification Code</label>
                            <div className="relative flex items-center">
                                <input
                                    type="text"
                                    required
                                    value={code}
                                    onChange={e => setCode(e.target.value)}
                                    className="w-full h-11 px-4 text-center tracking-widest text-lg font-medium rounded-lg bg-transparent border focus:outline-none transition-colors"
                                    style={{ borderColor: 'var(--color-border)', color: 'white' }}
                                    placeholder="000000"
                                    maxLength={6}
                                />
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full h-11 mt-2 rounded-lg text-white font-medium flex items-center justify-center gap-2 transition-opacity"
                        style={{ backgroundColor: 'var(--color-blue)', opacity: loading ? 0.7 : 1 }}
                    >
                        {loading ? <Loader2 size={16} className="spin" /> : mode === 'login' ? 'Sign In' : mode === 'signup' ? 'Create Account' : 'Verify'}
                        {!loading && <ChevronRight size={16} />}
                    </button>
                </form>

                <div className="mt-8 flex items-center gap-2 text-sm" style={{ color: 'var(--color-muted)' }}>
                    {mode === 'login' ? "Don't have an account?" : "Already have an account?"}
                    <button
                        type="button"
                        onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); setMessage(''); }}
                        className="font-medium hover:underline transition-all"
                        style={{ color: 'var(--color-blue)' }}
                    >
                        {mode === 'login' ? 'Sign up' : 'Sign in'}
                    </button>
                </div>
            </div>
        </div>
    );
}

function CheckCircle2({ size, className }: { size: number, className: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
    );
}
