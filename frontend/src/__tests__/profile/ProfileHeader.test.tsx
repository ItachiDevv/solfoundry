import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProfileHeader } from '../../components/profile/ProfileHeader';

const defaultProps = {
  githubUsername: 'contributor42',
  githubAvatar: 'https://avatars.githubusercontent.com/u/12345678?v=4',
  walletAddress: '7xKXtg2CW87d97TXJSDpbD5jBkheTqA7ECTACjHm4Dp',
  joinDate: '2025-01-15T10:30:00Z',
  reputationScore: 1580,
  reputationBadge: 'expert' as const,
};

describe('ProfileHeader', () => {
  it('renders the username', () => {
    render(<ProfileHeader {...defaultProps} />);
    expect(screen.getByTestId('profile-username')).toHaveTextContent('contributor42');
  });

  it('renders the avatar image', () => {
    render(<ProfileHeader {...defaultProps} />);
    const avatar = screen.getByTestId('profile-avatar') as HTMLImageElement;
    expect(avatar.src).toContain('avatars.githubusercontent.com');
    expect(avatar.alt).toContain('contributor42');
  });

  it('renders a truncated wallet address', () => {
    render(<ProfileHeader {...defaultProps} />);
    const wallet = screen.getByTestId('profile-wallet');
    expect(wallet).toHaveTextContent('7xKX...m4Dp');
  });

  it('renders the join date formatted', () => {
    render(<ProfileHeader {...defaultProps} />);
    const joinDate = screen.getByTestId('profile-join-date');
    expect(joinDate).toHaveTextContent('Joined January 2025');
  });

  it('renders the reputation badge with correct label', () => {
    render(<ProfileHeader {...defaultProps} />);
    expect(screen.getByTestId('profile-badge')).toHaveTextContent('Expert');
  });

  it('renders the reputation score', () => {
    render(<ProfileHeader {...defaultProps} />);
    expect(screen.getByTestId('profile-reputation-score')).toHaveTextContent('1,580 rep');
  });

  it('renders a GitHub link', () => {
    render(<ProfileHeader {...defaultProps} />);
    const link = screen.getByTestId('profile-github-link') as HTMLAnchorElement;
    expect(link.href).toBe('https://github.com/contributor42');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('renders different badge tiers correctly', () => {
    const { rerender } = render(<ProfileHeader {...defaultProps} reputationBadge="newcomer" />);
    expect(screen.getByTestId('profile-badge')).toHaveTextContent('Newcomer');
    rerender(<ProfileHeader {...defaultProps} reputationBadge="legend" />);
    expect(screen.getByTestId('profile-badge')).toHaveTextContent('Legend');
  });

  it('handles short wallet addresses gracefully', () => {
    render(<ProfileHeader {...defaultProps} walletAddress="shortAddr" />);
    expect(screen.getByTestId('profile-wallet')).toHaveTextContent('shortAddr');
  });
});
