import { Github, Twitter } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-foundry-border bg-foundry-bg px-6 py-6 lg:px-10">
      <div className="mx-auto flex max-w-screen-2xl flex-col items-center justify-between gap-4 sm:flex-row">
        <div className="flex items-center gap-2 text-sm text-foundry-text-dim">
          <span className="text-foundry-purple font-bold">S</span>
          <span>
            SolFoundry &copy; {new Date().getFullYear()} &mdash; Building the
            future of decentralized work
          </span>
        </div>

        <div className="flex items-center gap-4">
          <a
            href="https://github.com/solfoundry"
            target="_blank"
            rel="noopener noreferrer"
            className="text-foundry-text-dim hover:text-foundry-text transition-colors"
            aria-label="GitHub"
          >
            <Github size={18} />
          </a>
          <a
            href="https://twitter.com/solfoundry"
            target="_blank"
            rel="noopener noreferrer"
            className="text-foundry-text-dim hover:text-foundry-text transition-colors"
            aria-label="Twitter"
          >
            <Twitter size={18} />
          </a>
          <span className="text-xs text-foundry-text-dim">v0.1.0</span>
        </div>
      </div>
    </footer>
  );
}
