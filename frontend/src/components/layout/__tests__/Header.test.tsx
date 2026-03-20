import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { Header } from '../Header';

function renderHeader(props = {}) {
  const defaultProps = {
    sidebarCollapsed: false,
    onMenuClick: vi.fn(),
    theme: 'dark' as const,
    onToggleTheme: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <Header {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

describe('Header', () => {
  it('renders the header with banner role', () => {
    renderHeader();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders SolFoundry branding', () => {
    renderHeader();
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
    expect(screen.getByText('SF')).toBeInTheDocument();
  });

  it('renders nav links (Bounties, Leaderboard, Agents, Docs)', () => {
    renderHeader();
    expect(screen.getByText('Bounties')).toBeInTheDocument();
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
  });

  it('has main navigation aria label', () => {
    renderHeader();
    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument();
  });

  it('renders the wallet connect button', () => {
    renderHeader();
    expect(screen.getByText('Connect Wallet')).toBeInTheDocument();
  });

  it('wallet connect button has proper aria-label', () => {
    renderHeader();
    expect(screen.getByLabelText('Connect wallet')).toBeInTheDocument();
  });

  it('renders the search input', () => {
    renderHeader();
    expect(screen.getByLabelText('Search')).toBeInTheDocument();
  });

  it('renders notification bell', () => {
    renderHeader();
    expect(screen.getByLabelText('Notifications')).toBeInTheDocument();
  });

  it('renders user avatar dropdown', () => {
    renderHeader();
    expect(screen.getByLabelText('User menu')).toBeInTheDocument();
  });

  it('renders mobile hamburger menu button', () => {
    renderHeader();
    expect(screen.getByLabelText('Open navigation menu')).toBeInTheDocument();
  });

  it('calls onMenuClick when hamburger is clicked', async () => {
    const onMenuClick = vi.fn();
    renderHeader({ onMenuClick });
    await userEvent.click(screen.getByLabelText('Open navigation menu'));
    expect(onMenuClick).toHaveBeenCalledTimes(1);
  });

  it('renders theme toggle with correct label for dark mode', () => {
    renderHeader({ theme: 'dark' });
    expect(screen.getByLabelText('Switch to light mode')).toBeInTheDocument();
  });

  it('renders theme toggle with correct label for light mode', () => {
    renderHeader({ theme: 'light' });
    expect(screen.getByLabelText('Switch to dark mode')).toBeInTheDocument();
  });

  it('calls onToggleTheme when theme toggle is clicked', async () => {
    const onToggleTheme = vi.fn();
    renderHeader({ onToggleTheme });
    await userEvent.click(screen.getByLabelText('Switch to light mode'));
    expect(onToggleTheme).toHaveBeenCalledTimes(1);
  });

  it('focuses search on Ctrl+K', () => {
    renderHeader();
    const searchInput = screen.getByLabelText('Search');
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    expect(document.activeElement).toBe(searchInput);
  });

  it('renders nav links as anchor elements with correct paths', () => {
    renderHeader();
    const bountiesLink = screen.getByText('Bounties').closest('a');
    expect(bountiesLink).toHaveAttribute('href', '/bounties');
    const leaderboardLink = screen.getByText('Leaderboard').closest('a');
    expect(leaderboardLink).toHaveAttribute('href', '/leaderboard');
    const agentsLink = screen.getByText('Agents').closest('a');
    expect(agentsLink).toHaveAttribute('href', '/agents');
    const docsLink = screen.getByText('Docs').closest('a');
    expect(docsLink).toHaveAttribute('href', '/docs');
  });

  it('highlights active nav link', () => {
    render(
      <MemoryRouter initialEntries={['/bounties']}>
        <Header
          sidebarCollapsed={false}
          onMenuClick={vi.fn()}
          theme="dark"
          onToggleTheme={vi.fn()}
        />
      </MemoryRouter>,
    );
    const bountiesLink = screen.getByText('Bounties').closest('a');
    expect(bountiesLink?.className).toContain('brand-500');
  });
});
