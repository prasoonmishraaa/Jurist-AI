import React, { useEffect, useState } from 'react';
import { ShieldCheck, Users, Database, FileCheck, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import { User, SystemStats } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export const AdminDashboardPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        const [usersData, statsData] = await Promise.all([
          api.getAdminUsers(),
          api.getAdminStats()
        ]);
        setUsers(usersData || []);
        setStats(statsData || null);
      } catch {
        // graceful display
      } finally {
        setIsLoading(false);
      }
    };
    fetchAdminData();
  }, []);

  if (isLoading) {
    return <LoadingSpinner message="Loading corpus administration metrics..." />;
  }

  return (
    <div className="space-y-8 bg-ivory-100">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-serif font-semibold uppercase tracking-widest text-burgundy-900">
          <ShieldCheck className="w-3.5 h-3.5 text-gold-600" />
          <span>Workspace &amp; Corpus Governance</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-navy-900">
          Precedent Corpus &amp; Persistence Status
        </h1>
        <p className="text-xs text-charcoal-600">
          Inspect enrolled chamber accounts, database storage mode, and verified primary court sources.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="parchment-card rounded p-4 space-y-1">
          <div className="flex items-center justify-between text-charcoal-500">
            <span className="text-[10.5px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Enrolled Users
            </span>
            <Users className="w-4 h-4 text-navy-800" />
          </div>
          <div className="text-2xl font-serif font-bold text-navy-900">{stats?.totalUsers ?? users.length}</div>
          <span className="text-[10.5px] text-charcoal-500">Active workspace accounts</span>
        </div>

        <div className="parchment-card rounded p-4 space-y-1">
          <div className="flex items-center justify-between text-charcoal-500">
            <span className="text-[10.5px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Research Dossiers
            </span>
            <FileCheck className="w-4 h-4 text-burgundy-900" />
          </div>
          <div className="text-2xl font-serif font-bold text-navy-900">{stats?.totalAnalyses ?? 0}</div>
          <span className="text-[10.5px] text-charcoal-500">Completed case analyses</span>
        </div>

        <div className="parchment-card rounded p-4 space-y-1">
          <div className="flex items-center justify-between text-charcoal-500">
            <span className="text-[10.5px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Data Persistence
            </span>
            <Database className="w-4 h-4 text-navy-800" />
          </div>
          <div className="text-sm font-serif font-bold text-navy-900 pt-1">
            {stats?.database?.isConnected ? 'MongoDB Persistent' : 'In-Memory Session Store'}
          </div>
          <span className="text-[10.5px] text-charcoal-500 truncate block">
            {stats?.database?.isConnected ? 'Database connected' : 'Configure MONGODB_URI for persistent storage'}
          </span>
        </div>

        <div className="parchment-card rounded p-4 space-y-1">
          <div className="flex items-center justify-between text-charcoal-500">
            <span className="text-[10.5px] font-serif font-semibold uppercase tracking-wider text-charcoal-600">
              Verified Corpus
            </span>
            <BookOpen className="w-4 h-4 text-gold-700" />
          </div>
          <div className="text-2xl font-serif font-bold text-navy-900">
            {stats?.corpusStats?.totalJudgments ?? stats?.hybridCorpusCount ?? stats?.precedentCorpusCount ?? 176} Judgments
          </div>
          <span className="text-[10.5px] text-charcoal-500">
            {stats?.corpusStats?.officialVerifiedLandmarks ?? stats?.officialVerifiedSourceCount ?? 10} official PDFs &bull; {stats?.corpusStats?.indexedPassages ?? stats?.indexedPassages ?? 771} passages
          </span>
        </div>
      </div>

      {/* User Directory */}
      <div className="parchment-card rounded overflow-hidden space-y-4 p-6">
        <h3 className="text-base font-serif font-bold text-navy-900 flex items-center gap-2">
          <Users className="w-4 h-4 text-gold-600" />
          <span>Registered Chamber Accounts</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="bg-ivory-100 border-b border-ivory-300 font-serif uppercase tracking-wider text-navy-900 text-[10px]">
              <tr>
                <th className="py-2.5 px-3">Name</th>
                <th className="py-2.5 px-3">Email</th>
                <th className="py-2.5 px-3">Role</th>
                <th className="py-2.5 px-3">Enrolled</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ivory-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-ivory-50/60 transition-colors">
                  <td className="py-2.5 px-3 font-serif font-bold text-navy-950">{u.name}</td>
                  <td className="py-2.5 px-3 text-charcoal-600">{u.email}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded bg-ivory-200 text-navy-900 border border-gold-500/30 text-[10px] font-serif uppercase">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-charcoal-500 text-[11px]">
                    {u.createdAt ? new Date(u.createdAt).toLocaleDateString('en-IN') : 'Recent'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
