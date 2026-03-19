import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Footer } from '../Footer';

describe('Footer', () => {
  it('renders with contentinfo role', () => {
    render(<Footer />);
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('renders footer navigation links', () => {
    render(<Footer />);
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('Twitter')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
    expect(screen.getByText('CA')).toBeInTheDocument();
  });

  it('renders copyright notice with current year', () => {
    render(<Footer />);
    const year = new Date().getFullYear();
    expect(screen.getByText(new RegExp(`${year} SolFoundry`))).toBeInTheDocument();
  });

  it('has external links with proper attributes', () => {
    render(<Footer />);
    const githubLink = screen.getByText('GitHub').closest('a');
    expect(githubLink).toHaveAttribute('target', '_blank');
    expect(githubLink).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('has footer navigation aria label', () => {
    render(<Footer />);
    expect(screen.getByLabelText('Footer navigation')).toBeInTheDocument();
  });
});
