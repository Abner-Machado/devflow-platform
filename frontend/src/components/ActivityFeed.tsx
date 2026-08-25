/** Renders the activity log rows shared by the dashboard and the Activity page. */

import type { Activity, ActivityAction } from "../api/types";
import { formatRelative } from "../lib/format";

const TONE: Record<ActivityAction, { background: string; color: string; glyph: string }> = {
  project_created: { background: "var(--brand-50)", color: "var(--brand-600)", glyph: "P" },
  project_updated: { background: "var(--neutral-bg)", color: "var(--text-muted)", glyph: "P" },
  project_deleted: { background: "var(--danger-bg)", color: "var(--danger)", glyph: "P" },
  task_created: { background: "var(--info-bg)", color: "var(--info)", glyph: "T" },
  task_updated: { background: "var(--neutral-bg)", color: "var(--text-muted)", glyph: "T" },
  task_completed: { background: "var(--success-bg)", color: "var(--success)", glyph: "OK" },
  task_deleted: { background: "var(--danger-bg)", color: "var(--danger)", glyph: "T" },
  document_created: { background: "var(--warning-bg)", color: "var(--warning)", glyph: "D" },
  document_updated: { background: "var(--neutral-bg)", color: "var(--text-muted)", glyph: "D" },
  document_deleted: { background: "var(--danger-bg)", color: "var(--danger)", glyph: "D" },
};

export function ActivityFeed({ items }: { items: Activity[] }) {
  return (
    <ul className="feed" style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {items.map((activity) => {
        const tone = TONE[activity.action];
        return (
          <li className="feed-item" key={activity.id}>
            <span
              className="feed-icon"
              style={{ background: tone.background, color: tone.color }}
              aria-hidden="true"
            >
              {tone.glyph}
            </span>
            <span className="feed-text">
              <span>You {activity.summary}</span>
              <span className="feed-meta">
                {activity.project_name ? `${activity.project_name} - ` : ""}
                {formatRelative(activity.created_at)}
              </span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}
