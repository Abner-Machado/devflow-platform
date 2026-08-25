/** Formatting helpers shared across pages. */

import type { Priority, ProjectStatus, TaskStatus } from "../api/types";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return dateFormatter.format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return dateTimeFormatter.format(new Date(value));
}

/** Compact relative time, e.g. "3h ago". Falls back to a date past a week. */
export function formatRelative(value: string): string {
  const then = new Date(value).getTime();
  const seconds = Math.round((Date.now() - then) / 1000);

  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return formatDate(value);
}

export function isOverdue(dueDate: string | null, status: TaskStatus): boolean {
  if (!dueDate || status === "done") return false;
  return new Date(dueDate).getTime() < Date.now();
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

const TITLES: Record<string, string> = {
  planning: "Planning",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  archived: "Archived",
  todo: "To do",
  in_progress: "In progress",
  in_review: "In review",
  done: "Done",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function label(value: string): string {
  return TITLES[value] ?? value.replace(/_/g, " ");
}

export type Tone = "neutral" | "success" | "warning" | "danger" | "info" | "brand";

export function projectStatusTone(status: ProjectStatus): Tone {
  switch (status) {
    case "active":
      return "success";
    case "planning":
      return "info";
    case "paused":
      return "warning";
    case "completed":
      return "brand";
    default:
      return "neutral";
  }
}

export function taskStatusTone(status: TaskStatus): Tone {
  switch (status) {
    case "done":
      return "success";
    case "in_progress":
      return "info";
    case "in_review":
      return "brand";
    default:
      return "neutral";
  }
}

export function priorityTone(priority: Priority): Tone {
  switch (priority) {
    case "critical":
      return "danger";
    case "high":
      return "warning";
    case "medium":
      return "info";
    default:
      return "neutral";
  }
}

export const PROJECT_STATUSES: ProjectStatus[] = [
  "planning",
  "active",
  "paused",
  "completed",
  "archived",
];
export const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];
export const PRIORITIES: Priority[] = ["low", "medium", "high", "critical"];

/** Value for a datetime-local input, in the browser's timezone. */
export function toDateTimeLocal(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function fromDateTimeLocal(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}
