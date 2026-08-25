import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { Button, Field, Input } from "../components/ui/Primitives";
import { InlineError } from "../components/ui/States";
import { AuthScreen } from "./LoginPage";

const MIN_PASSWORD_LENGTH = 8;

export function RegisterPage() {
  const { register, status } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "authenticated") return <Navigate to="/" replace />;

  const fieldError = (field: string) =>
    error instanceof ApiError ? error.fieldError(field) : undefined;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(new Error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`));
      return;
    }

    setSubmitting(true);
    try {
      await register(fullName.trim(), email.trim(), password);
      navigate("/", { replace: true });
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
          <h1>Create your account</h1>
          <p className="muted" style={{ fontSize: "var(--text-sm)" }}>
            It takes a few seconds. No credit card, no email confirmation.
          </p>
        </div>

        {error && !fieldError("email") ? <InlineError error={error} /> : null}

        <Field label="Full name" htmlFor="full_name" error={fieldError("full_name")}>
          <Input
            id="full_name"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
            autoFocus
          />
        </Field>

        <Field label="Email" htmlFor="email" error={fieldError("email")}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
          error={fieldError("password")}
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={MIN_PASSWORD_LENGTH}
          />
        </Field>

        <Button variant="primary" type="submit" loading={submitting} block>
          Create account
        </Button>

        <p className="subtle">
          Already registered? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </AuthScreen>
  );
}
