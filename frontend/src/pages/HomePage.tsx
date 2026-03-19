import { Link } from "react-router-dom";
import { ArrowRight, Target, Trophy, Bot, Coins, Zap, Shield } from "lucide-react";

const stats = [
  { label: "Total Bounties", value: "1,247", icon: Target },
  { label: "Active Contributors", value: "3,891", icon: Trophy },
  { label: "SOL Distributed", value: "45,230", icon: Coins },
  { label: "AI Agents", value: "24", icon: Bot },
];

const features = [
  {
    icon: Target,
    title: "Bounty Board",
    description:
      "Browse, claim, and complete bounties. Rewards held in on-chain escrow until work is verified.",
    link: "/bounties",
  },
  {
    icon: Bot,
    title: "AI Agents",
    description:
      "Autonomous agents that assist with code review, testing, documentation, and security analysis.",
    link: "/agents",
  },
  {
    icon: Trophy,
    title: "Reputation System",
    description:
      "Build your on-chain reputation. Top contributors earn badges, streaks, and bonus multipliers.",
    link: "/leaderboard",
  },
  {
    icon: Coins,
    title: "FORGE Tokenomics",
    description:
      "Deflationary token powering the ecosystem. Stake, govern, and earn from platform fees.",
    link: "/tokenomics",
  },
  {
    icon: Zap,
    title: "Instant Settlement",
    description:
      "No waiting. Approved bounties settle immediately through Solana smart contracts.",
    link: "/bounties",
  },
  {
    icon: Shield,
    title: "Escrow Protection",
    description:
      "Funds locked in program-owned accounts. Automatic refund if deadlines expire without completion.",
    link: "/bounties",
  },
];

export function HomePage() {
  return (
    <div className="animate-fade-in">
      {/* Hero */}
      <section className="py-12 lg:py-20">
        <div className="max-w-3xl">
          <div className="badge-purple mb-6">Open Source Bounty Platform</div>
          <h1 className="text-4xl font-bold leading-tight tracking-tight lg:text-5xl">
            The{" "}
            <span className="gradient-text-purple">Foundry Floor</span>
            <br />
            Where Code Meets{" "}
            <span className="gradient-text-green">Capital</span>
          </h1>
          <p className="mt-6 text-lg text-foundry-text-muted leading-relaxed max-w-2xl">
            Decentralized bounty platform on Solana. Post bounties, complete
            work, earn crypto. AI agents assist every step. All backed by
            on-chain escrow.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/bounties" className="btn-primary inline-flex items-center gap-2">
              Browse Bounties
              <ArrowRight size={16} />
            </Link>
            <Link to="/bounties/create" className="btn-secondary inline-flex items-center gap-2">
              Post a Bounty
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="card">
              <Icon size={20} className="text-foundry-purple mb-3" />
              <div className="text-2xl font-bold text-foundry-text">
                {stat.value}
              </div>
              <div className="text-xs text-foundry-text-dim mt-1">
                {stat.label}
              </div>
            </div>
          );
        })}
      </section>

      {/* Features */}
      <section className="mt-16">
        <h2 className="text-2xl font-bold mb-8">How It Works</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Link
                key={feature.title}
                to={feature.link}
                className="card-interactive group"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-foundry-purple/10 mb-4 group-hover:bg-foundry-purple/20 transition-colors">
                  <Icon size={20} className="text-foundry-purple" />
                </div>
                <h3 className="text-base font-semibold mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-foundry-text-muted leading-relaxed">
                  {feature.description}
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="mt-16 mb-8 rounded-xl border border-foundry-purple/20 bg-gradient-to-br from-foundry-purple/5 to-transparent p-8 lg:p-12 glow-purple">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-bold mb-3">Ready to Build?</h2>
          <p className="text-foundry-text-muted mb-6">
            Connect your wallet, browse open bounties, and start earning. No
            middlemen, no delays &mdash; just code and crypto.
          </p>
          <Link
            to="/bounties"
            className="btn-success inline-flex items-center gap-2"
          >
            Get Started
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  );
}
