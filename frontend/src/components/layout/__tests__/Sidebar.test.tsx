import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { Sidebar } from '../Sidebar';

function renderSidebar(props = {}) {
  const defaultProps = {
    collapsed: false,
    onToggle: vi.fn(),
    mobileOpen: false,
    onMobileClose: vi.fn(),
  };
  return render(
    <MemoryRouter>
      <Sidebar {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

describe('Sidebar', () => {
  it('renders navigation with correct aria label', () => {
    renderSidebar();
    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument();
  });

  it('renders correct nav items (Bounties, Leaderboard, Agents, Docs)', () => {
    renderSidebar();
    expect(screen.getByText('Bounties')).toBeInTheDocument();
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
    expect(screen.getByText('Agents')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
  });

  it('does not render old nav items', () => {
    renderSidebar();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Projects')).not.toBeInTheDocument();
    expect(screen.queryByText('Automations')).not.toBeInTheDocument();
    expect(screen.queryByText('Analytics')).not.toBeInTheDocument();
  });

  it('renders SolFoundry logo and name when not collapsed', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
    expect(screen.getByText('SF')).toBeInTheDocument();
  });

  it('renders $FNDRY token badge when not collapsed', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByText('$FNDRY')).toBeInTheDocument();
    expect(screen.getByText('on Solana')).toBeInTheDocument();
  });

  it('hides nav labels when collapsed', () => {
    renderSidebar({ collapsed: true });
    expect(screen.queryByText('Bounties')).not.toBeInTheDocument();
  });

  it('hides $FNDRY badge when collapsed', () => {
    renderSidebar({ collapsed: true });
    expect(screen.queryByText('$FNDRY')).not.toBeInTheDocument();
  });

  it('shows mobile overlay when mobileOpen is true', () => {
    renderSidebar({ mobileOpen: true });
    expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();
  });

  it('does not show mobile overlay when mobileOpen is false', () => {
    renderSidebar({ mobileOpen: false });
    expect(screen.queryByTestId('sidebar-overlay')).not.toBeInTheDocument();
  });

  it('calls onMobileClose when overlay is clicked', async () => {
    const onMobileClose = vi.fn();
    renderSidebar({ mobileOpen: true, onMobileClose });
    await userEvent.click(screen.getByTestId('sidebar-overlay'));
    expect(onMobileClose).toHaveBeenCalledTimes(1);
  });

  it('calls onMobileClose when Escape key is pressed', () => {
    const onMobileClose = vi.fn();
    renderSidebar({ mobileOpen: true, onMobileClose });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onMobileClose).toHaveBeenCalledTimes(1);
  });

  it('shows close button in mobile view', () => {
    renderSidebar({ mobileOpen: true });
    expect(screen.getByLabelText('Close navigation menu')).toBeInTheDocument();
  });

  it('calls onMobileClose when close button is clicked', async () => {
    const onMobileClose = vi.fn();
    renderSidebar({ mobileOpen: true, onMobileClose });
    await userEvent.click(screen.getByLabelText('Close navigation menu'));
    expect(onMobileClose).toHaveBeenCalledTimes(1);
  });

  it('renders version info when not collapsed', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByText('SolFoundry v0.1.0')).toBeInTheDocument();
  });

  it('hides version info when collapsed', () => {
    renderSidebar({ collapsed: true });
    expect(screen.queryByText('SolFoundry v0.1.0')).not.toBeInTheDocument();
  });

  it('renders home link with SolFoundry Home label', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByLabelText('SolFoundry Home')).toBeInTheDocument();
  });

  it('renders nav links with correct paths', () => {
    renderSidebar();
    const bountiesLink = screen.getByText('Bounties').closest('a');
    expect(bountiesLink).toHaveAttribute('href', '/bounties');
    const leaderboardLink = screen.getByText('Leaderboard').closest('a');
    expect(leaderboardLink).toHaveAttribute('href', '/leaderboard');
  });

  it('highlights active nav item', () => {
    render(
      <MemoryRouter initialEntries={['/bounties']}>
        <Sidebar collapsed={false} onToggle={vi.fn()} mobileOpen={false} onMobileClose={vi.fn()} />
      </MemoryRouter>,
    );
    const bountiesLink = screen.getByText('Bounties').closest('a');
    expect(bountiesLink?.className).toContain('brand-500');
  });
});
