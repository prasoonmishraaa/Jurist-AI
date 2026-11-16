import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Scale, LogOut, LayoutDashboard, BookOpen, PlusCircle, Menu } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface NavbarProps {
  onToggleSidebar?: () => void;
  showSidebarToggle?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar, showSidebarToggle = false }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-40 bg-navy-900 border-b border-gold-500/25 text-white shadow-judicial no-print">
      <div className="h-1 w-full bg-gradient-to-r from-burgundy-900 via-gold-500 to-burgundy-900" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          {showSidebarToggle && onToggleSidebar && (
            <button
              type="button"
              onClick={onToggleSidebar}
              aria-label="Open workspace navigation"
              className="lg:hidden p-2 rounded text-gold-300 hover:bg-navy-800 border border-gold-500/25 shrink-0"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <Link to="/" className="flex items-center space-x-3 group min-w-0 shrink-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded bg-navy-950 flex items-center justify-center border border-gold-500/40 group-hover:border-gold-500 transition-colors shrink-0">
              <Scale className="w-5 h-5 text-gold-400" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-serif font-bold text-lg sm:text-xl tracking-wider text-white flex items-center gap-1.5 leading-tight whitespace-nowrap">
                JURIST <span className="text-gold-400 font-sans font-semibold text-base sm:text-lg tracking-normal">AI</span>
              </span>
              <span className="hidden sm:block text-[9.5px] text-gold-300/80 uppercase font-sans tracking-widest leading-none whitespace-nowrap">
                Indian Legal Research &amp; Litigation Support
              </span>
            </div>
          </Link>
        </div>

        <nav
          className={`${
            showSidebarToggle ? 'hidden xl:flex' : 'hidden md:flex'
          } items-center space-x-6 text-xs uppercase tracking-wider font-medium text-charcoal-200 whitespace-nowrap`}
        >
          <Link
            to={user ? '/dashboard/precedents' : '/precedents'}
            className="hover:text-gold-400 transition-colors flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 text-gold-500/80" />
            <span>Precedent Library</span>
          </Link>
          {location.pathname === '/' ? (
            <>
              <a href="#methodology" className="hover:text-gold-400 transition-colors">
                Methodology
              </a>
              <a href="#compliance" className="hover:text-gold-400 transition-colors">
                Authority Standards
              </a>
              <a href="#disclaimer" className="hover:text-gold-400 transition-colors">
                Legal Notice
              </a>
            </>
          ) : (
            <Link to="/#methodology" className="hover:text-gold-400 transition-colors">
              Research Framework
            </Link>
          )}
        </nav>

        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          {user ? (
            <div className="flex items-center space-x-2 sm:space-x-3">
              <Link
                to="/dashboard/new-analysis"
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold bg-burgundy-900 hover:bg-burgundy-850 text-gold-200 border border-gold-500/30 transition-colors shadow-sm"
              >
                <PlusCircle className="w-3.5 h-3.5 text-gold-400" />
                <span>New Case Brief</span>
              </Link>
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-navy-800 text-charcoal-100 hover:bg-navy-700 border border-navy-700 transition-colors"
              >
                <LayoutDashboard className="w-3.5 h-3.5 text-gold-400" />
                <span className="hidden xs:inline sm:inline">Workspace</span>
              </Link>
              <button
                type="button"
                onClick={handleLogout}
                className="text-charcoal-300 hover:text-burgundy-300 p-1.5 rounded hover:bg-navy-800 transition-colors"
                title="Sign out"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2 sm:space-x-3 text-xs font-medium uppercase tracking-wider">
              <Link to="/login" className="text-charcoal-200 hover:text-white px-2.5 sm:px-3 py-1.5 transition-colors">
                Sign In
              </Link>
              <Link
                to="/register"
                className="bg-gold-500 hover:bg-gold-600 text-navy-950 font-semibold px-3 sm:px-4 py-1.5 rounded border border-gold-400/80 transition-colors shadow-sm whitespace-nowrap"
              >
                Open Workspace
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
