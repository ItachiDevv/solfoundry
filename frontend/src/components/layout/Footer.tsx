interface FooterLink {
  label: string;
  href: string;
  external?: boolean;
}

const footerLinks: FooterLink[] = [
  { label: 'GitHub', href: 'https://github.com/solfoundry', external: true },
  { label: 'Twitter', href: 'https://twitter.com/solfoundry', external: true },
  { label: 'Docs', href: '/docs' },
  { label: 'CA', href: '#', external: false },
];

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer
      className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-surface px-4 sm:px-6 py-4 font-mono"
      role="contentinfo"
    >
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Links */}
        <nav className="flex items-center gap-4" aria-label="Footer navigation">
          {footerLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              target={link.external ? '_blank' : undefined}
              rel={link.external ? 'noopener noreferrer' : undefined}
              className="text-xs text-gray-500 dark:text-gray-400 hover:text-brand-500 dark:hover:text-brand-400
                         transition-colors"
            >
              {link.label}
              {link.external && (
                <svg className="inline-block h-3 w-3 ml-0.5 -mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
              )}
            </a>
          ))}
        </nav>

        {/* Copyright */}
        <p className="text-xs text-gray-400 dark:text-gray-600">
          &copy; {currentYear} SolFoundry. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
