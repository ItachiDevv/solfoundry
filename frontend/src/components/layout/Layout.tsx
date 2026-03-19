import { useState, useEffect, type ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('sf-theme');
      if (stored === 'light' || stored === 'dark') return stored;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark';
  });

  // Apply theme class to document
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('sf-theme', theme);
  }, [theme]);

  // Close mobile menu on resize to desktop
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileMenuOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    document.body.style.overflow = mobileMenuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [mobileMenuOpen]);

  const toggleTheme = () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  const toggleSidebar = () => setSidebarCollapsed((prev) => !prev);
  const openMobileMenu = () => setMobileMenuOpen(true);
  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-surface font-mono">
      {/* Sidebar - desktop persistent, mobile overlay */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        mobileOpen={mobileMenuOpen}
        onMobileClose={closeMobileMenu}
      />

      {/* Main content area - offset by sidebar width on desktop */}
      <div
        className={`flex flex-col min-h-screen transition-all duration-200
                    ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}`}
      >
        <Header
          sidebarCollapsed={sidebarCollapsed}
          onMenuClick={openMobileMenu}
          theme={theme}
          onToggleTheme={toggleTheme}
        />

        {/* Page content slot */}
        <main className="flex-1 p-4 sm:p-6" role="main">
          {children}
        </main>

        <Footer />
      </div>
    </div>
  );
}
