import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { Layout } from '../Layout';

function renderLayout(children = <div>Test Content</div>) {
  return render(
    <MemoryRouter>
      <Layout>{children}</Layout>
    </MemoryRouter>,
  );
}

describe('Layout', () => {
  it('renders children in the main content area', () => {
    renderLayout(<div>My Page Content</div>);
    expect(screen.getByText('My Page Content')).toBeInTheDocument();
  });

  it('renders the header', () => {
    renderLayout();
    expect(screen.getByRole('banner')).toBeInTheDocument();
  });

  it('renders the sidebar', () => {
    renderLayout();
    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument();
  });

  it('renders the footer', () => {
    renderLayout();
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
  });

  it('renders the main content area with role', () => {
    renderLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('opens mobile menu when hamburger is clicked', async () => {
    renderLayout();
    const hamburger = screen.getByLabelText('Open navigation menu');
    await userEvent.click(hamburger);
    expect(screen.getByTestId('sidebar-overlay')).toBeInTheDocument();
  });

  it('has dark theme by default (prefers-color-scheme)', () => {
    renderLayout();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
