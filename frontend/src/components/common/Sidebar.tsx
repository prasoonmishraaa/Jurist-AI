import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  History,
  Bookmark,
  BookOpen,
  User,
  ShieldCheck,
  Scale,
  X
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  onNavigate?: () => void;
  showCloseButton?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onNavigate, showCloseButton = false, onClose }) => {
  const { user } = useAuth();

  const links = [
    { to: '/dashboard', label: 'Workspace Overview', icon: LayoutDashboard, end: true },
    { to: '/dashboard/new-analysis', label: 'New Case Analysis', icon: PlusCircle },
    { to: '/dashboard/history', label: 'Case History', icon: History },
    { to: '/dashboard/saved', label: 'Saved Authorities', icon: Bookmark },
    { to: '/dashboard/precedents', label: 'Precedent Corpus', icon: BookOpen },
    { to: '/dashboard/profile', label: 'Practitioner Profile', icon: User }
  ];

  if (user?.role === 'admin') {
    links.push({ to: '/dashboard/admin', label: 'Corpus Administration', icon: ShieldCheck });
  }

  return (
    <aside className="w-64 bg-navy-950 border-r border-gold-500/20 h-full flex flex-col justify-between p-4 text-charcoal-300 select-none">
      <div className="space-y-5">
        {showCloseButton && (
          <div className="flex items-center justify-between lg:hidden pb-2 border-b border-navy-800">
            <span className="text-xs font-serif font-semibold text-gold-300 tracking-wider uppercase">
              Research Menu
            </span>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close workspace navigation"
              className="p-1.5 rounded text-charcoal-300 hover:bg-navy-800 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="bg-navy-900 rounded p-3.5 border border-gold-500/20 flex items-center space-x-3">
          <div className="w-10 h-10 rounded bg-navy-950 border border-gold-500/40 flex items-center justify-center font-serif font-bold text-gold-400 text-base shrink-0">
            {user?.name ? user.name.charAt(0).toUpperCase() : 'C'}
          </div>
          <div className="overflow-hidden min-w-0">
            <h4 className="text-xs font-semibold font-serif text-white truncate tracking-wide">
              {user?.name || 'Legal Researcher'}
            </h4>
            <span className="text-[10px] text-gold-400/80 uppercase font-sans tracking-wider block truncate">
              {user?.role === 'admin' ? 'Corpus Administrator' : 'Advocate / Legal Researcher'}
            </span>
          </div>
        </div>

        <div className="px-2">
          <span className="text-[10px] uppercase tracking-widest font-semibold text-gold-500/70">
            Research Dossiers
          </span>
        </div>

        <nav className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-navy-900 text-gold-300 border-l-2 border-gold-500'
                      : 'text-charcoal-300 hover:bg-navy-900/70 hover:text-white'
                  }`
                }
              >
                <Icon className="w-4 h-4 text-gold-400/80 shrink-0" />
                <span className="truncate">{link.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="pt-4 border-t border-navy-800 text-[11px] text-charcoal-400 space-y-2">
        <div className="flex items-center gap-1.5 text-gold-400/90 font-serif font-medium text-xs">
          <Scale className="w-3.5 h-3.5 text-gold-400 shrink-0" />
          <span>Research &amp; Drafting Aid</span>
        </div>
        <p className="leading-relaxed text-[10.5px] text-charcoal-400">
          Structured statutory mapping, primary judgment links, and draft grounds require independent verification by counsel before court filing.
        </p>
      </div>
    </aside>
  );
};
