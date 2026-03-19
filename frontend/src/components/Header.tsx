import { Link, useLocation } from "react-router-dom";
import { Menu, Moon, Sun, X } from "lucide-react";
import { useState } from "react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { useTheme } from "../providers/ThemeProvider";
import { useAuth } from "../providers/AuthProvider";

const navLinks = [
  { path: "/bounties", label: "Bounties" },
  { path: "/leaderboard", label: "Leaderboard" },
  { path: "/agents", label: "Agents" },
  { path: "/tokenomics", label: "Tokenomics" },
];

export function Header() {
  const { theme, toggleTheme } = useTheme();
  const { isAuthenticated, user } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-foundry-border bg-foundry-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-screen-2xl items-center justify-between px-4 lg:px-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-foundry-purple glow-purple">
            <span className="text-lg font-bold text-white">S</span>
          </div>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-foundry-purple">Sol</span>
            <span className="text-foundry-text">Foundry</span>
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => {
            const isActive = location.pathname.startsWith(link.path);
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-foundry-purple/10 text-foundry-purple"
                    : "text-foundry-text-muted hover:text-foundry-text hover:bg-foundry-surface"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-lg p-2 text-foundry-text-muted hover:bg-foundry-surface hover:text-foundry-text transition-colors"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          {/* Auth-gated links */}
          {isAuthenticated && (
            <Link
              to="/dashboard"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-foundry-text-muted hover:text-foundry-text hover:bg-foundry-surface transition-colors md:block"
            >
              {user?.username ?? "Dashboard"}
            </Link>
          )}

          {/* Wallet button */}
          <div className="[&_.wallet-adapter-button]:!bg-foundry-purple [&_.wallet-adapter-button]:!rounded-lg [&_.wallet-adapter-button]:!font-mono [&_.wallet-adapter-button]:!text-sm [&_.wallet-adapter-button]:!h-9">
            <WalletMultiButton />
          </div>

          {/* Mobile menu toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-lg p-2 text-foundry-text-muted hover:bg-foundry-surface md:hidden"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile nav */}
      {mobileMenuOpen && (
        <nav className="border-t border-foundry-border bg-foundry-bg px-4 py-4 md:hidden animate-slide-down">
          {navLinks.map((link) => {
            const isActive = location.pathname.startsWith(link.path);
            return (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-foundry-purple/10 text-foundry-purple"
                    : "text-foundry-text-muted hover:text-foundry-text"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          {isAuthenticated && (
            <Link
              to="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="block rounded-lg px-3 py-2.5 text-sm font-medium text-foundry-text-muted hover:text-foundry-text"
            >
              Dashboard
            </Link>
          )}
        </nav>
      )}
    </header>
  );
}
