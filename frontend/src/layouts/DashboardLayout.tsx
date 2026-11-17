import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from '../components/common/Navbar';
import { Sidebar } from '../components/common/Sidebar';

export const DashboardLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-ivory-100 text-charcoal-800">
      <Navbar showSidebarToggle onToggleSidebar={() => setMobileMenuOpen((v) => !v)} />

      <div className="flex-1 flex relative">
        {/* Desktop Persistent Sidebar */}
        <div className="hidden lg:block shrink-0 min-h-[calc(100vh-4.25rem)] no-print">
          <Sidebar />
        </div>

        {/* Mobile / Tablet Slide-Over Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden flex no-print">
            <div
              className="fixed inset-0 bg-navy-950/70 backdrop-blur-[1px]"
              onClick={() => setMobileMenuOpen(false)}
            />
            <div className="relative z-10 h-full max-w-[80vw]">
              <Sidebar
                showCloseButton
                onClose={() => setMobileMenuOpen(false)}
                onNavigate={() => setMobileMenuOpen(false)}
              />
            </div>
          </div>
        )}

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full min-w-0 overflow-x-hidden bg-ivory-100">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
