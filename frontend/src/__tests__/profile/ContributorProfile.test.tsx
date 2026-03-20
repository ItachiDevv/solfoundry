import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ContributorProfile } from '../../components/profile/ContributorProfile';
import { mockContributorProfile } from '../../data/mockProfile';

describe('ContributorProfile', () => {
  it('renders the full profile page', () => {
    render(<ContributorProfile profile={mockContributorProfile} />);
    expect(screen.getByTestId('contributor-profile')).toBeInTheDocument();
  });

  it('renders all major sections', () => {
    render(<ContributorProfile profile={mockContributorProfile} />);
    expect(screen.getByTestId('profile-header')).toBeInTheDocument();
    expect(screen.getByTestId('stats-cards')).toBeInTheDocument();
    expect(screen.getByTestId('profile-earnings-chart')).toBeInTheDocument();
    expect(screen.getByTestId('bounty-history')).toBeInTheDocument();
    expect(screen.getByTestId('reputation-breakdown')).toBeInTheDocument();
    expect(screen.getByTestId('hire-agent-button')).toBeInTheDocument();
  });

  it('displays the hire as agent button', () => {
    render(<ContributorProfile profile={mockContributorProfile} />);
    const button = screen.getByTestId('hire-agent-button');
    expect(button).toHaveTextContent('Hire as Agent');
  });
});
