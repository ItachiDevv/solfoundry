import { Link, useLocation } from "react-router-dom";
import {
  Home,
  Target,
  Trophy,
  Bot,
  Coins,
  LayoutDashboard,
  UserCircle,
  PlusCircle,
} from "lucide-react";
import { useAuth } from "../providers/AuthProvider";

interface NavItem {
  path: string;
  label: string;
  icon: React.ElementType;
  authRequired?: boolean;
}

const navItems: NavItem[] = [
  { path: "/", label: "Home", icon: Home },
  { path: "/bounties", label: "Bounties", icon: Target },
  { path: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { path: "/agents", label: "Agents", icon: Bot },
  { path: "/tokenomics", label: "Tokenomics", icon: Coins },
];

const authNavItems: NavItem[] = [
  {
    path: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    authRequired: true,
  },
  {
    path: "/bounties/create",
    label: "Create Bounty",
    icon: PlusCircle,
    authRequired: true,
  },
  {
    path: "/profile",
    label: "Profile",
    icon: UserCircle,
    authRequired: true,
  },
];

export function Sidebar() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  function isActive(path: string): boolean {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  }

  return (
    <aside className="hidden w-60 shrink-0 border-r border-foundry-border bg-foundry-bg lg:block">
      <nav className="sticky top-16 flex flex-col gap-1 p-4">
        {/* Main nav */}
        <div className="mb-2">
          <span className="px-3 text-[10px] font-semibold uppercase tracking-wider text-foundry-text-dim">
            Navigation
          </span>
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.path);
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 ${
                active
                  ? "bg-foundry-purple/10 text-foundry-purple"
                  : "text-foundry-text-muted hover:bg-foundry-surface hover:text-foundry-text"
              }`}
            >
              <Icon size={18} className={active ? "text-foundry-purple" : ""} />
              {item.label}
            </Link>
          );
        })}

        {/* Auth-gated nav */}
        {isAuthenticated && (
          <>
            <div className="mb-2 mt-6">
              <span className="px-3 text-[10px] font-semibold uppercase tracking-wider text-foundry-text-dim">
                Your Space
              </span>
            </div>
            {authNavItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 ${
                    active
                      ? "bg-foundry-purple/10 text-foundry-purple"
                      : "text-foundry-text-muted hover:bg-foundry-surface hover:text-foundry-text"
                  }`}
                >
                  <Icon
                    size={18}
                    className={active ? "text-foundry-purple" : ""}
                  />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}

        {/* Stats footer */}
        <div className="mt-auto pt-8">
          <div className="rounded-lg border border-foundry-border bg-foundry-surface p-4">
            <div className="text-xs text-foundry-text-dim mb-2">
              Network Status
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-foundry-green animate-pulse-glow" />
              <span className="text-xs text-foundry-green">Devnet Live</span>
            </div>
          </div>
        </div>
      </nav>
    </aside>
  );
}
