import { render, screen } from '@testing-library/react';
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

  it('renders updated nav items (Bounties, Leaderboard, Agents, Docs)', () => {
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
    expect(screen.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('renders SolFoundry logo and name when not collapsed', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByText('SolFoundry')).toBeInTheDocument();
  });

  it('hides nav labels when collapsed', () => {
    renderSidebar({ collapsed: true });
    expect(screen.queryByText('Bounties')).not.toBeInTheDocument();
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

  it('renders version info when not collapsed', () => {
    renderSidebar({ collapsed: false });
    expect(screen.getByText('SolFoundry v0.1.0')).toBeInTheDocument();
  });
});
