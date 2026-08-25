import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Button, Field, Input } from "../components/ui/Primitives";
import { InlineError } from "../components/ui/States";

export function AuthScreen({ children }: { children: ReactNode }) {
  return (
    <div className="auth-screen">
      <aside className="auth-aside">
        <div className="row">
          <span className="sidebar-mark" aria-hidden="true">
            D
          </span>
          <strong style={{ fontSize: "var(--text-lg)" }}>DevFlow</strong>
        </div>
        <h2>Every project, task and decision in one panel.</h2>
        <p>
          Track delivery without stitching four tools together. Projects, tasks, technical docs
          and the metrics that come out of them - from the same database.
        </p>
        <ul className="auth-points">
          <li>Progress computed from real task counts, never typed in by hand.</li>
          <li>An activity log written by the same code path that changes state.</li>
          <li>Markdown documentation that lives next to the project it describes.</li>
        </ul>
      </aside>
      <main className="auth-panel">{children}</main>
    </div>
  );
}

export function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/" replace />;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      const target = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(target, { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught : new Error("Could not reach the API. Is it running?"),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthScreen>
      <form className="auth-form" onSubmit={onSubmit} noValidate>
        <div>
          <h1>Sign in</h1>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            Welcome back. Enter your credentials to continue.
          </p>
        </div>

        {error ? <InlineError error={error} /> : null}

        <Field label="Email" htmlFor="email">
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            autoFocus
          />
        </Field>

        <Field label="Password" htmlFor="password">
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </Field>

        <Button variant="primary" type="submit" loading={submitting} block>
          Sign in
        </Button>

        <p className="subtle">
          No account yet? <Link to="/register">Create one</Link>
        </p>

        <p className="auth-demo">
          Seeded development database? Sign in with <strong>demo@devflow.dev</strong> /{" "}
          <strong>demo12345</strong>.
        </p>
      </form>
    </AuthScreen>
  );
}
