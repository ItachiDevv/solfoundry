import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach } from 'vitest';
import { Layout } from '../Layout';

function renderLayout(children = <div>Test Content</div>, route = '/') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Layout>{children}</Layout>
    </MemoryRouter>,
  );
}

describe('Layout', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('renders children in the main content area', () => {
    renderLayout(<div>My Page Content</div>);
    expect(screen.getByText('My Page Content')).toBeInTheDocument();
  });

  it('renders the header', () => {
    renderLayout();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders the sidebar navigation', () => {
    renderLayout();
    expect(screen.getAllByLabelText('Main navigation').length).toBeGreaterThan(0);
  });

  it('renders the footer', () => {
    renderLayout();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('renders the main content area with role', () => {
    renderLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  describe('hamburger menu interaction', () => {
    it('opens mobile sidebar when hamburger is clicked', async () => {
      renderLayout();
      const hamburger = screen.getByLabelText('Open navigation menu');
      await userEvent.click(hamburger);
      expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();
    });

    it('closes mobile sidebar when overlay is clicked', async () => {
      renderLayout();
      await userEvent.click(screen.getByLabelText('Open navigation menu'));
      expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();

      await userEvent.click(screen.getByTestId('sidebar-overlay'));
      expect(screen.queryByTestId('sidebar-overlay')).not.toBeInTheDocument();
    });

    it('closes mobile sidebar when Escape key is pressed', async () => {
      renderLayout();
      await userEvent.click(screen.getByLabelText('Open navigation menu'));
      expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();

      fireEvent.keyDown(document, { key: 'Escape' });
      expect(screen.queryByTestId('sidebar-overlay')).not.toBeInTheDocument();
    });

    it('closes mobile sidebar when close button is clicked', async () => {
      renderLayout();
      await userEvent.click(screen.getByLabelText('Open navigation menu'));
      expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();

      const closeBtn = screen.getByLabelText('Close navigation menu');
      await userEvent.click(closeBtn);
      expect(screen.queryByTestId('sidebar-overlay')).not.toBeInTheDocument();
    });
  });

  describe('theme toggle interaction', () => {
    it('toggles from dark to light mode', async () => {
      renderLayout();
      const toggle = screen.getByLabelText('Switch to light mode');
      await userEvent.click(toggle);
      expect(screen.getByLabelText('Switch to dark mode')).toBeInTheDocument();
    });

    it('toggles from light back to dark mode', async () => {
      renderLayout();
      const toggleToLight = screen.getByLabelText('Switch to light mode');
      await userEvent.click(toggleToLight);
      expect(screen.getByLabelText('Switch to dark mode')).toBeInTheDocument();

      const toggleToDark = screen.getByLabelText('Switch to dark mode');
      await userEvent.click(toggleToDark);
      expect(screen.getByLabelText('Switch to light mode')).toBeInTheDocument();
    });

    it('persists theme preference in localStorage', async () => {
      renderLayout();
      await userEvent.click(screen.getByLabelText('Switch to light mode'));
      expect(localStorage.getItem('sf-theme')).toBe('light');
    });

    it('applies dark class to document.documentElement', () => {
      localStorage.setItem('sf-theme', 'dark');
      renderLayout();
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('navigation links', () => {
    it('renders all four nav links (Bounties, Leaderboard, Agents, Docs)', () => {
      renderLayout();
      expect(screen.getAllByText('Bounties').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Leaderboard').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Agents').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Docs').length).toBeGreaterThan(0);
    });

    it('highlights active nav link based on current route', () => {
      renderLayout(<div>Bounties Page</div>, '/bounties');
      const bountyLinks = screen.getAllByText('Bounties');
      const activeBountyLink = bountyLinks.find(el => {
        const parent = el.closest('a');
        return parent?.className.includes('brand-500');
      });
      expect(activeBountyLink).toBeDefined();
    });
  });

  describe('SolFoundry branding', () => {
    it('displays SolFoundry logo', () => {
      renderLayout();
      const logos = screen.getAllByText('SF');
      expect(logos.length).toBeGreaterThan(0);
    });

    it('displays SolFoundry name', () => {
      renderLayout();
      const names = screen.getAllByText('SolFoundry');
      expect(names.length).toBeGreaterThan(0);
    });

    it('displays $FNDRY token badge', () => {
      renderLayout();
      expect(screen.getAllByText('$FNDRY').length).toBeGreaterThan(0);
    });

    it('renders Connect Wallet button', () => {
      renderLayout();
      expect(screen.getByText('Connect Wallet')).toBeInTheDocument();
    });
  });
});
