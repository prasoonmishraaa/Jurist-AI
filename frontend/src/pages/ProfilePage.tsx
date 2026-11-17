import React, { useState } from 'react';
import { User, Lock, CheckCircle, AlertCircle, Shield, Gavel } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';

export const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [isUpdatingName, setIsUpdatingName] = useState(false);
  const [nameSuccess, setNameSuccess] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [passError, setPassError] = useState<string | null>(null);
  const [passSuccess, setPassSuccess] = useState(false);

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdatingName(true);
    setNameSuccess(false);
    try {
      await api.updateProfile({ name });
      await refreshUser();
      setNameSuccess(true);
      setTimeout(() => setNameSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.error || 'Failed to update practitioner name.');
    } finally {
      setIsUpdatingName(false);
    }
  };

  const handleUpdatePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPassError(null);
    setPassSuccess(false);

    if (newPassword !== confirmPassword) {
      setPassError('New access keys do not match.');
      return;
    }

    if (newPassword.length < 6) {
      setPassError('Access key must be at least 6 characters long.');
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await api.updatePassword({ currentPassword, newPassword });
      setPassSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPassSuccess(false), 3000);
    } catch (err: any) {
      setPassError(err.response?.data?.error || 'Failed to update access key.');
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-8 bg-ivory-100">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
          <User className="w-3.5 h-3.5 text-gold-600" />
          <span>Counsel Credentials</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-navy-900">Practitioner Profile & Security</h1>
        <p className="text-xs text-charcoal-600">
          Manage your research chamber identity, email address, and authentication keys.
        </p>
      </div>

      {/* Account Info Card */}
      <div className="bg-white rounded border border-gold-500/30 p-6 shadow-judicial parchment-card space-y-4">
        <h2 className="text-base font-serif font-bold text-navy-900 flex items-center gap-2">
          <Gavel className="w-4 h-4 text-gold-600" />
          <span>Practitioner Identity</span>
        </h2>

        {nameSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-300 rounded text-xs text-emerald-900 flex items-center gap-2 font-sans">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Chamber title updated successfully.</span>
          </div>
        )}

        <form onSubmit={handleUpdateName} className="space-y-4 font-sans text-xs">
          <div>
            <label className="block font-serif font-semibold text-charcoal-700 mb-1">
              Advocate / Researcher Full Name
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 font-sans"
            />
          </div>

          <div>
            <label className="block font-serif font-semibold text-charcoal-700 mb-1">
              Registered Chamber Email (Read-only)
            </label>
            <input
              type="email"
              disabled
              value={user?.email || ''}
              className="w-full px-3.5 py-2 text-sm bg-ivory-200 border border-ivory-300 rounded text-charcoal-500 cursor-not-allowed font-sans"
            />
          </div>

          <div>
            <label className="block font-serif font-semibold text-charcoal-700 mb-1">Chamber Role</label>
            <span className="inline-block px-3 py-1 rounded bg-navy-950 text-gold-300 border border-gold-500/30 font-serif uppercase tracking-widest text-[10px]">
              {user?.role === 'admin' ? 'Corpus Administrator' : 'Legal Researcher / Advocate'}
            </span>
          </div>

          <button
            type="submit"
            disabled={isUpdatingName}
            className="px-4 py-2 bg-navy-900 hover:bg-navy-850 text-gold-300 font-serif font-semibold rounded border border-gold-500/40 text-xs transition-colors shadow-sm disabled:opacity-50"
          >
            {isUpdatingName ? 'Updating Chamber Record...' : 'Update Chamber Title'}
          </button>
        </form>
      </div>

      {/* Security Credentials Card */}
      <div className="bg-white rounded border border-gold-500/30 p-6 shadow-judicial parchment-card space-y-4">
        <h2 className="text-base font-serif font-bold text-navy-900 flex items-center gap-2">
          <Lock className="w-4 h-4 text-burgundy-900" />
          <span>Update Chamber Password</span>
        </h2>

        {passSuccess && (
          <div className="p-3 bg-emerald-50 border border-emerald-300 rounded text-xs text-emerald-900 flex items-center gap-2 font-sans">
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>Password updated successfully.</span>
          </div>
        )}

        {passError && (
          <div className="p-3 bg-burgundy-50 border border-burgundy-200 rounded text-xs text-burgundy-900 flex items-center gap-2 font-sans">
            <AlertCircle className="w-4 h-4 text-burgundy-700 shrink-0" />
            <span>{passError}</span>
          </div>
        )}

        <form onSubmit={handleUpdatePassword} className="space-y-4 font-sans text-xs">
          <div>
            <label className="block font-serif font-semibold text-charcoal-700 mb-1">
              Current Access Password
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 font-sans"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-serif font-semibold text-charcoal-700 mb-1">
                New Access Password
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 font-sans"
              />
            </div>

            <div>
              <label className="block font-serif font-semibold text-charcoal-700 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2 text-sm bg-ivory-50 border border-ivory-300 rounded focus:outline-none focus:border-gold-500 font-sans"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isUpdatingPassword}
            className="px-4 py-2 bg-navy-900 hover:bg-navy-850 text-gold-300 font-serif font-semibold rounded border border-gold-500/40 text-xs transition-colors shadow-sm disabled:opacity-50"
          >
            {isUpdatingPassword ? 'Updating Password...' : 'Save New Password'}
          </button>
        </form>
      </div>
    </div>
  );
};
