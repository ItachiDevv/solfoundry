import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ThemeToggle } from '../ThemeToggle';

describe('ThemeToggle', () => {
  it('shows switch to light mode label in dark theme', () => {
    render(<ThemeToggle theme="dark" onToggle={vi.fn()} />);
    expect(screen.getByLabelText('Switch to light mode')).toBeInTheDocument();
  });

  it('shows switch to dark mode label in light theme', () => {
    render(<ThemeToggle theme="light" onToggle={vi.fn()} />);
    expect(screen.getByLabelText('Switch to dark mode')).toBeInTheDocument();
  });

  it('calls onToggle when clicked', async () => {
    const onToggle = vi.fn();
    render(<ThemeToggle theme="dark" onToggle={onToggle} />);
    await userEvent.click(screen.getByLabelText('Switch to light mode'));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
