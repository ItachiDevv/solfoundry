import { NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';

interface NavItem {
  label: string;
  path: string;
  icon: JSX.Element;
}

const navItems: NavItem[] = [
  {
    label: 'Bounties',
    path: '/bounties',
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
  {
    label: 'Leaderboard',
    path: '/leaderboard',
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 0 1 3 3h-15a3 3 0 0 1 3-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497" />
      </svg>
    ),
  },
  {
    label: 'Agents',
    path: '/agents',
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3" />
      </svg>
    ),
  },
  {
    label: 'Docs',
    path: '/docs',
    icon: (
      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
      </svg>
    ),
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen = false, onMobileClose }: SidebarProps) {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileOpen && onMobileClose) {
        onMobileClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [mobileOpen, onMobileClose]);

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
          data-testid="sidebar-overlay"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-gray-200 dark:border-gray-800
                    bg-white dark:bg-surface transition-all duration-200 font-mono
                    ${collapsed ? 'w-16' : 'w-64'}
                    ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}
        aria-label="Main navigation"
      >
        <div className="flex h-14 items-center justify-between border-b border-gray-200 dark:border-gray-800 px-4">
          {!collapsed && (
            <NavLink to="/" className="flex items-center gap-2" aria-label="SolFoundry Home">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-solana-green flex items-center justify-center">
                <span className="text-white font-bold text-sm">SF</span>
              </div>
              <span className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
                SolFoundry
              </span>
            </NavLink>
          )}
          {collapsed && (
            <NavLink to="/" className="flex items-center justify-center w-full" aria-label="SolFoundry Home">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-solana-green flex items-center justify-center">
                <span className="text-white font-bold text-sm">SF</span>
              </div>
            </NavLink>
          )}
          <button
            type="button"
            onClick={onToggle}
            className={`inline-flex h-8 w-8 items-center justify-center rounded-lg
                       text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                       hover:bg-gray-100 dark:hover:bg-gray-800
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500
                       ${collapsed ? 'hidden' : 'hidden lg:inline-flex'}`}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5" />
            </svg>
          </button>
          {mobileOpen && (
            <button
              type="button"
              onClick={onMobileClose}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg
                         text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
                         hover:bg-gray-100 dark:hover:bg-gray-800
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500
                         lg:hidden"
              aria-label="Close navigation menu"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto p-3 space-y-1" aria-label="Sidebar navigation">
          {navItems.map((item) => (
            <div key={item.path} className="relative">
              <NavLink
                to={item.path}
                onClick={onMobileClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
                   ${isActive
                     ? 'bg-brand-500/10 text-brand-500 dark:text-brand-400 border-l-2 border-brand-500'
                     : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                   } ${collapsed ? 'justify-center px-2 border-l-0' : ''}`
                }
                onMouseEnter={() => setHoveredItem(item.path)}
                onMouseLeave={() => setHoveredItem(null)}
                aria-label={item.label}
              >
                {item.icon}
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
              {collapsed && hoveredItem === item.path && (
                <div
                  role="tooltip"
                  className="absolute left-full top-1/2 -translate-y-1/2 ml-2 rounded-md bg-gray-900 dark:bg-gray-100
                             px-2 py-1 text-xs font-medium text-white dark:text-gray-900 shadow-lg whitespace-nowrap z-50"
                >
                  {item.label}
                </div>
              )}
            </div>
          ))}
        </nav>

        {!collapsed && (
          <div className="border-t border-gray-200 dark:border-gray-800 p-4 space-y-2">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-gray-400 dark:text-gray-500 border border-gray-200 dark:border-gray-700 rounded px-1.5 py-0.5 font-semibold">
                $FNDRY
              </span>
              <span className="text-[10px] text-gray-400 dark:text-gray-600">
                on Solana
              </span>
            </div>
            <p className="text-xs text-gray-400 dark:text-gray-600">
              SolFoundry v0.1.0
            </p>
          </div>
        )}
      </aside>
    </>
  );
}
