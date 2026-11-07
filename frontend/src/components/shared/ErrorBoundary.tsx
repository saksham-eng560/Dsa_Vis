/** Contain render errors (e.g. an unexpected visualisation payload) to one pane. */
import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  label: string;
  children: ReactNode;
}

export class ErrorBoundary extends Component<Props, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[CodeLens] ${this.props.label} crashed`, error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div role="alert" className="glass flex flex-col items-center gap-3 p-8 text-center">
        <p className="font-semibold">The {this.props.label} hit an unexpected error.</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{this.state.error.message}</p>
        <button className="btn" onClick={() => this.setState({ error: null })}>Try again</button>
      </div>
    );
  }
}
