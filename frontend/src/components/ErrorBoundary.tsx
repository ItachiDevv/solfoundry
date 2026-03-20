/**
 * Error boundary with retry support.
 * Catches render errors and shows a fallback UI with retry button.
 * @module components/ErrorBoundary
 */
import React from 'react';

interface Props { children: React.ReactNode; fallback?: (error: Error, retry: () => void) => React.ReactNode; }
interface State { error: Error | null; }

/** Class-based error boundary (required by React for error catching). */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) { super(props); this.state = { error: null }; }

  static getDerivedStateFromError(error: Error): State { return { error }; }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleRetry = (): void => { this.setState({ error: null }); };

  render(): React.ReactNode {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) return this.props.fallback(error, this.handleRetry);
      return (
        <div className="p-8 max-w-lg mx-auto text-center space-y-4" role="alert">
          <div className="text-red-400 text-lg font-semibold">Something went wrong</div>
          <p className="text-gray-400 text-sm">{error.message}</p>
          <button onClick={this.handleRetry}
            className="px-4 py-2 bg-[#9945FF] hover:bg-[#7a35cc] text-white rounded-lg text-sm transition-colors">
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
