import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          height: '100%', padding: 40, fontFamily: 'var(--font-body)',
        }}>
          <div style={{
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 12, padding: 40, maxWidth: 500, textAlign: 'center',
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
            <h2 style={{ color: 'var(--text)', fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
              Something went wrong
            </h2>
            <p style={{ color: 'var(--text2)', fontSize: 14, marginBottom: 20 }}>
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              style={{
                background: 'var(--accent)', color: '#fff', border: 'none',
                borderRadius: 8, padding: '10px 24px', fontSize: 14, cursor: 'pointer',
                fontWeight: 500,
              }}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
