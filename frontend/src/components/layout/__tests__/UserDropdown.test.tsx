import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { UserDropdown } from '../UserDropdown';

describe('UserDropdown', () => {
  it('renders the avatar button', () => {
    render(<UserDropdown />);
    expect(screen.getByLabelText('User menu')).toBeInTheDocument();
  });

  it('does not show dropdown menu initially', () => {
    render(<UserDropdown />);
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('shows dropdown menu when avatar is clicked', async () => {
    render(<UserDropdown />);
    await userEvent.click(screen.getByLabelText('User menu'));
    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  it('shows Profile and Settings options in dropdown', async () => {
    render(<UserDropdown />);
    await userEvent.click(screen.getByLabelText('User menu'));
    expect(screen.getByText('Profile')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows Disconnect option in dropdown', async () => {
    render(<UserDropdown />);
    await userEvent.click(screen.getByLabelText('User menu'));
    expect(screen.getByText('Disconnect')).toBeInTheDocument();
  });

  it('closes dropdown when clicking Disconnect', async () => {
    render(<UserDropdown />);
    await userEvent.click(screen.getByLabelText('User menu'));
    await userEvent.click(screen.getByText('Disconnect'));
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
