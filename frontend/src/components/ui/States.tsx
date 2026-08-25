/**
 * Loading, empty and error states.
 *
 * Every list and panel in the app renders one of these three, so a screen never
 * shows a blank rectangle while it waits, and never fails silently.
 */

import type { ReactNode } from "react";

import { ApiError } from "../../api/client";
import { Button } from "./Primitives";

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function LoadingRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="stack" style={{ padding: "1.5rem" }} aria-busy="true" aria-live="polite">
      <span className="visually-hidden">Loading</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} height={index === 0 ? 20 : 14} width={index === 0 ? "40%" : "100%"} />
      ))}
    </div>
  );
}

export function LoadingCards({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cards" aria-busy="true">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="card">
          <div className="card-body stack">
            <Skeleton height={18} width="60%" />
            <Skeleton height={12} width="90%" />
            <Skeleton height={8} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon = "+",
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="state">
      <span className="state-icon" aria-hidden="true">
        {icon}
      </span>
      <p className="state-title">{title}</p>
      {description && <p className="state-text">{description}</p>}
      {action}
    </div>
  );
}

/** Turns any thrown value into something a user can act on. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof ApiError
      ? error.message
      : error instanceof Error
        ? "The server could not be reached. Check that the API is running."
        : "Something went wrong.";

  return (
    <div className="state state-error" role="alert">
      <span className="state-icon" aria-hidden="true">
        !
      </span>
      <p className="state-title">Could not load this view</p>
      <p className="state-text">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function InlineError({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p className="inline-error" role="alert">
      {message}
    </p>
  );
}

export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <span>
        Page {page} of {pages} - {total} item{total === 1 ? "" : "s"}
      </span>
      <span className="row">
        <Button size="sm" onClick={() => onChange(page - 1)} disabled={page <= 1}>
          Previous
        </Button>
        <Button size="sm" onClick={() => onChange(page + 1)} disabled={page >= pages}>
          Next
        </Button>
      </span>
    </nav>
  );
}
