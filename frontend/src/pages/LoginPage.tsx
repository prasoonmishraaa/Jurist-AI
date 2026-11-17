import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Scale, Lock, Mail, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to authenticate counsel. Please verify credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-ivory-100">
      <div className="max-w-md w-full bg-white border border-gold-500/30 rounded p-8 shadow-judicial space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded bg-navy-950 border border-gold-500/50 flex items-center justify-center mx-auto text-gold-400 shadow-sm">
            <Scale className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-navy-900">Counsel Chamber Login</h2>
          <p className="text-xs text-charcoal-500">
            Access litigation research dossiers and court submissions
          </p>
        </div>

        {error && (
          <div className="p-3 bg-burgundy-50 border border-burgundy-900/30 rounded text-xs text-burgundy-900 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-burgundy-800" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-serif font-semibold text-charcoal-700 mb-1">Counsel Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="counsel@highcourt.in"
                className="w-full pl-9 pr-3 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 focus:ring-1 focus:ring-gold-500 transition-all font-sans"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-serif font-semibold text-charcoal-700">Chamber Access Key / Password</label>
              <button
                type="button"
                onClick={() =>
                  setError(
                    'Password reset emails are not enabled on this deployment. Register a new chamber profile or contact your workspace administrator.'
                  )
                }
                className="text-[11px] text-burgundy-900 hover:underline"
              >
                Reset Access?
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-charcoal-400 absolute left-3 top-3" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 focus:ring-1 focus:ring-gold-500 transition-all font-sans"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 bg-navy-900 hover:bg-navy-850 text-gold-300 font-serif font-semibold rounded border border-gold-500/40 transition-colors shadow-sm disabled:opacity-50 text-sm flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <span>Authenticating Counsel...</span>
            ) : (
              <>
                <span>Enter Research Chamber</span>
                <ArrowRight className="w-4 h-4 text-gold-400" />
              </>
            )}
          </button>
        </form>

        <div className="pt-4 border-t border-ivory-200 text-center space-y-2">
          <p className="text-xs text-charcoal-500">
            New advocate or legal researcher?{' '}
            <Link to="/register" className="font-semibold text-burgundy-900 hover:underline">
              Register Chamber Account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
