import { Component, type ErrorInfo, type ReactNode } from "react";
import styles from "./ErrorBoundary.module.css";

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Render error:", error.message, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className={styles.wrap} role="alert">
        <h1>Something went wrong</h1>
        <p>The page hit an unexpected problem. Reloading usually fixes it.</p>
        <button type="button" className={styles.button} onClick={() => window.location.assign("/")}>
          Reload HealthNexus
        </button>
      </main>
    );
  }
}
