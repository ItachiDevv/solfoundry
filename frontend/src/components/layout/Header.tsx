import { useState, useRef, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { UserDropdown } from './UserDropdown';

interface HeaderProps {
  sidebarCollapsed: boolean;
  onMenuClick: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

const navLinks = [
  { label: 'Bounties', path: '/bounties' },
  { label: 'Leaderboard', path: '/leaderboard' },
  { label: 'Agents', path: '/agents' },
  { label: 'Docs', path: '/docs' },
];

export function Header({ onMenuClick, theme, onToggleTheme }: HeaderProps) {
  const [searchFocused, setSearchFocused] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <header
      className="sticky top-0 z-20 flex h-14 items-center justify-between border-b
                 border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-surface/80
                 backdrop-blur-md px-4 sm:px-6 font-mono"
      role="banner"
    >
      {/* Left: Logo + Mobile menu + Nav + Search */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={onMenuClick}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg
                     text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                     hover:bg-gray-100 dark:hover:bg-gray-800
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500
                     lg:hidden"
          aria-label="Open navigation menu"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
        </button>

        {/* Logo (visible on desktop) */}
        <NavLink to="/" className="hidden lg:flex items-center gap-2 mr-4 shrink-0" aria-label="SolFoundry Home">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-solana-green flex items-center justify-center">
            <span className="text-white font-bold text-sm">SF</span>
          </div>
          <span className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
            SolFoundry
          </span>
        </NavLink>

        {/* Desktop nav links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
          {navLinks.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) =>
                `relative px-3 py-1.5 text-sm font-medium rounded-md transition-colors
                 ${isActive
                   ? 'text-brand-500 bg-brand-500/10'
                   : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                 }`
              }
            >
              {({ isActive }) => (
                <>
                  {link.label}
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 bg-brand-500 rounded-full" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Search bar */}
        <div
          className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 transition-colors
                      ${searchFocused
                        ? 'border-brand-400 bg-white dark:bg-gray-800 ring-2 ring-brand-500/20'
                        : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50'
                      } flex-1 max-w-xs ml-auto`}
        >
          <svg className="h-4 w-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            ref={searchInputRef}
            type="search"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            className="w-full bg-transparent text-sm text-gray-900 dark:text-gray-100
                       placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none font-mono"
            aria-label="Search"
          />
          <kbd
            className="hidden sm:inline-flex items-center rounded border border-gray-200 dark:border-gray-700
                       bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-[10px] font-medium
                       text-gray-500 dark:text-gray-400"
          >
            {"⌘K"}
          </kbd>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 ml-4">
        {/* Wallet connect button placeholder */}
        <button
          type="button"
          className="hidden sm:inline-flex items-center gap-2 rounded-lg px-3 py-1.5
                     bg-gradient-to-r from-brand-500 to-brand-600
                     hover:from-brand-600 hover:to-brand-700
                     text-white text-sm font-medium
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2
                     dark:focus-visible:ring-offset-surface transition-all"
          aria-label="Connect wallet"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3" />
          </svg>
          Connect Wallet
        </button>

        <ThemeToggle theme={theme} onToggle={onToggleTheme} />

        {/* Notification bell */}
        <button
          type="button"
          className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg
                     text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200
                     hover:bg-gray-100 dark:hover:bg-gray-800
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          aria-label="Notifications"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
          </svg>
        </button>

        {/* User avatar dropdown */}
        <UserDropdown />
      </div>
    </header>
  );
}
