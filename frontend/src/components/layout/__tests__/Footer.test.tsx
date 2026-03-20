import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Footer } from '../Footer';

describe('Footer', () => {
  it('renders with contentinfo role', () => {
    render(<Footer />);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('renders SolFoundry branding in footer', () => {
    render(<Footer />);
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
    expect(screen.getByText('SF')).toBeInTheDocument();
  });

  it('renders $FNDRY token badge', () => {
    render(<Footer />);
    expect(screen.getByText('$FNDRY')).toBeInTheDocument();
  });

  it('renders footer navigation links', () => {
    render(<Footer />);
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('Twitter')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
  });

  it('renders copyright notice with current year and tagline', () => {
    render(<Footer />);
    const year = new Date().getFullYear();
    expect(screen.getByText(new RegExp(`${year} SolFoundry`))).toBeInTheDocument();
    expect(screen.getByText(/Autonomous AI Software Factory on Solana/)).toBeInTheDocument();
  });

  it('has external links with proper attributes', () => {
    render(<Footer />);
    const githubLink = screen.getByText('GitHub').closest('a');
    expect(githubLink).toHaveAttribute('target', '_blank');
    expect(githubLink).toHaveAttribute('rel', 'noopener noreferrer');

    const twitterLink = screen.getByText('Twitter').closest('a');
    expect(twitterLink).toHaveAttribute('target', '_blank');
    expect(twitterLink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('has internal links without target=_blank', () => {
    render(<Footer />);
    const docsLink = screen.getByText('Docs').closest('a');
    expect(docsLink).not.toHaveAttribute('target');
  });

  it('has footer navigation aria label', () => {
    render(<Footer />);
    expect(screen.getByLabelText('Footer navigation')).toBeInTheDocument();
  });
});
