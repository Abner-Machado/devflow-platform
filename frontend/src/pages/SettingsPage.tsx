import { useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { Button, Card, CardBody, CardHeader, Field, Input } from "../components/ui/Primitives";
import { InlineError } from "../components/ui/States";
import { useTheme } from "../hooks/useTheme";
import { useToast } from "../hooks/useToast";
import { formatDate } from "../lib/format";

const MIN_PASSWORD_LENGTH = 8;

export function SettingsPage() {
  const { user, setUser, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { notify } = useToast();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password && password.length < MIN_PASSWORD_LENGTH) {
      setError(new Error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`));
      return;
    }

    setSaving(true);
    try {
      const payload: Record<string, string> = { full_name: fullName.trim() };
      if (password) payload.password = password;
      const updated = await api.patch<User>("/users/me", payload);
      setUser(updated);
      setPassword("");
      notify("Profile updated.", "success");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new Error("Could not save your profile."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Your profile and how the interface looks.</p>
        </div>
      </header>

      <div className="grid grid-split">
        <Card>
          <CardHeader title="Profile" />
          <CardBody>
            <form className="stack" onSubmit={onSubmit} noValidate>
              {error ? <InlineError error={error} /> : null}

              <Field label="Full name" htmlFor="full-name">
                <Input
                  id="full-name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                />
              </Field>

              <Field label="Email" htmlFor="email" hint="Email cannot be changed after signup.">
                <Input id="email" value={user?.email ?? ""} disabled />
              </Field>

              <Field
                label="New password"
                htmlFor="new-password"
                hint={`Leave blank to keep the current one. At least ${MIN_PASSWORD_LENGTH} characters.`}
              >
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>

              <div className="row">
                <Button variant="primary" type="submit" loading={saving}>
                  Save changes
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>

        <div className="stack">
          <Card>
            <CardHeader title="Appearance" />
            <CardBody>
              <div className="row-between">
                <div>
                  <p style={{ fontWeight: 600 }}>Theme</p>
                  <p className="subtle">
                    Currently {theme}. Without a choice, DevFlow follows your system.
                  </p>
                </div>
                <Button onClick={toggle}>Switch to {theme === "dark" ? "light" : "dark"}</Button>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Account" />
            <CardBody>
              <div className="stack">
                <div className="row-between">
                  <span className="muted">Member since</span>
                  <span>{formatDate(user?.created_at)}</span>
                </div>
                <div className="row-between">
                  <span className="muted">Account ID</span>
                  <span className="mono">{user?.id}</span>
                </div>
                <div className="row-between">
                  <span className="muted">Session</span>
                  <Button size="sm" variant="ghost" onClick={() => void logout()}>
                    Sign out everywhere
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </>
  );
}
