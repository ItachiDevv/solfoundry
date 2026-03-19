import { render, screen } from '@testing-library/react';
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

  it('renders the wallet connect button', () => {
    renderHeader();
    expect(screen.getByText('Connect Wallet')).toBeInTheDocument();
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

  it('renders theme toggle', () => {
    renderHeader({ theme: 'dark' });
    expect(screen.getByLabelText('Switch to light mode')).toBeInTheDocument();
  });
});
