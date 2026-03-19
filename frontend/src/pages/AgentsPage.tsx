import { useState } from "react";
import {
  Bot,
  Search,
  Star,
  Zap,
  Shield,
  FileText,
  TestTube,
  Code,
} from "lucide-react";

interface MockAgent {
  id: string;
  name: string;
  description: string;
  category: string;
  rating: number;
  totalRuns: number;
  pricePerRun: number;
  status: "active" | "beta";
  icon: React.ElementType;
}

const MOCK_AGENTS: MockAgent[] = [
  {
    id: "1",
    name: "CodeReview Pro",
    description:
      "Automated code review with security analysis, style checks, and performance suggestions.",
    category: "code_review",
    rating: 4.8,
    totalRuns: 12450,
    pricePerRun: 0.5,
    status: "active",
    icon: Code,
  },
  {
    id: "2",
    name: "TestForge",
    description:
      "Generates comprehensive test suites for Rust/Anchor programs and TypeScript clients.",
    category: "testing",
    rating: 4.6,
    totalRuns: 8920,
    pricePerRun: 1.0,
    status: "active",
    icon: TestTube,
  },
  {
    id: "3",
    name: "DocWriter",
    description:
      "Auto-generates documentation, README files, and API references from code.",
    category: "documentation",
    rating: 4.5,
    totalRuns: 6780,
    pricePerRun: 0.3,
    status: "active",
    icon: FileText,
  },
  {
    id: "4",
    name: "AuditShield",
    description:
      "Security audit agent specializing in Solana programs. Detects common vulnerabilities.",
    category: "security",
    rating: 4.9,
    totalRuns: 3450,
    pricePerRun: 2.5,
    status: "active",
    icon: Shield,
  },
  {
    id: "5",
    name: "OptimizeBot",
    description:
      "Analyzes compute unit usage and suggests optimizations for on-chain programs.",
    category: "optimization",
    rating: 4.3,
    totalRuns: 1890,
    pricePerRun: 1.5,
    status: "beta",
    icon: Zap,
  },
  {
    id: "6",
    name: "BountyMatcher",
    description:
      "AI agent that analyzes your skills and matches you with the best bounties.",
    category: "optimization",
    rating: 4.1,
    totalRuns: 920,
    pricePerRun: 0.2,
    status: "beta",
    icon: Bot,
  },
];

const categories = [
  { key: "all", label: "All Agents" },
  { key: "code_review", label: "Code Review" },
  { key: "testing", label: "Testing" },
  { key: "documentation", label: "Documentation" },
  { key: "security", label: "Security" },
  { key: "optimization", label: "Optimization" },
];

export function AgentsPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");

  const filtered = MOCK_AGENTS.filter((a) => {
    const matchesSearch =
      !search || a.name.toLowerCase().includes(search.toLowerCase());
    const matchesCategory =
      category === "all" || a.category === category;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">AI Agent Marketplace</h1>
        <p className="text-sm text-foundry-text-muted mt-1">
          Autonomous agents to accelerate your bounty workflow
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row mb-6">
        <div className="relative flex-1">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-foundry-text-dim"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agents..."
            className="input-field w-full pl-10"
          />
        </div>
        <div className="flex gap-1 flex-wrap">
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => setCategory(cat.key)}
              className={`rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                category === cat.key
                  ? "bg-foundry-purple text-white"
                  : "bg-foundry-surface text-foundry-text-muted hover:text-foundry-text border border-foundry-border"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Agent grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((agent) => {
          const Icon = agent.icon;
          return (
            <div key={agent.id} className="card-interactive">
              <div className="flex items-start justify-between mb-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-foundry-purple/10">
                  <Icon size={24} className="text-foundry-purple" />
                </div>
                {agent.status === "beta" && (
                  <span className="badge border bg-orange-500/15 text-orange-400 border-orange-500/25">
                    BETA
                  </span>
                )}
              </div>

              <h3 className="font-semibold mb-1">{agent.name}</h3>
              <p className="text-sm text-foundry-text-muted leading-relaxed mb-4">
                {agent.description}
              </p>

              <div className="flex items-center justify-between pt-4 border-t border-foundry-border">
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 text-yellow-400">
                    <Star size={12} />
                    {agent.rating}
                  </span>
                  <span className="text-foundry-text-dim">
                    {agent.totalRuns.toLocaleString()} runs
                  </span>
                </div>
                <div className="text-sm font-bold text-foundry-green">
                  {agent.pricePerRun} FORGE
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="card text-center py-12">
          <Bot size={32} className="mx-auto text-foundry-text-dim mb-3" />
          <p className="text-foundry-text-muted">
            No agents found matching your criteria.
          </p>
        </div>
      )}
    </div>
  );
}
