import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ContributorProfilePage } from '../../pages/ContributorProfilePage';

describe('ContributorProfilePage', () => {
  it('renders profile with mock data fallback', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('API not available'));
    render(<ContributorProfilePage />);
    await vi.waitFor(() => { expect(screen.getByTestId('contributor-profile')).toBeInTheDocument(); });
    vi.restoreAllMocks();
  });

  it('shows loading state when fetch is pending', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}));
    render(<ContributorProfilePage />);
    expect(screen.getByTestId('profile-loading')).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
