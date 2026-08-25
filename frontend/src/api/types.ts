/** Types mirroring the API schemas exposed at /openapi.json. */

export type ProjectStatus = "planning" | "active" | "paused" | "completed" | "archived";
export type Priority = "low" | "medium" | "high" | "critical";
export type TaskStatus = "todo" | "in_progress" | "in_review" | "done";

export type ActivityAction =
  | "project_created"
  | "project_updated"
  | "project_deleted"
  | "task_created"
  | "task_updated"
  | "task_completed"
  | "task_deleted"
  | "document_created"
  | "document_updated"
  | "document_deleted";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface UserSummary {
  id: string;
  full_name: string;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ProjectStats {
  total_tasks: number;
  open_tasks: number;
  completed_tasks: number;
  document_count: number;
  progress: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  priority: Priority;
  repository_url: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
  stats: ProjectStats;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: Priority;
  due_date: string | null;
  completed_at: string | null;
  project_id: string;
  project_name: string | null;
  assignee_id: string | null;
  assignee: UserSummary | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  project_id: string;
  project_name: string | null;
  excerpt: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail {
  id: string;
  title: string;
  content: string;
  project_id: string;
  project_name: string | null;
  author: UserSummary | null;
  created_at: string;
  updated_at: string;
}

export interface Activity {
  id: string;
  action: ActivityAction;
  entity_type: string;
  entity_id: string | null;
  entity_title: string;
  summary: string;
  project_id: string | null;
  project_name: string | null;
  created_at: string;
}

export interface MetricsOverview {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  total_tasks: number;
  open_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  total_documents: number;
  completion_rate: number;
}

export interface ActivityPoint {
  day: string;
  created: number;
  completed: number;
}

export interface MetricsResponse {
  overview: MetricsOverview;
  tasks_by_status: { status: TaskStatus; count: number }[];
  tasks_by_priority: { priority: Priority; count: number }[];
  activity_series: ActivityPoint[];
  period_days: number;
}

export interface DashboardResponse {
  overview: MetricsOverview;
  recent_activity: Activity[];
  active_projects: Project[];
  upcoming_tasks: Task[];
  activity_series: ActivityPoint[];
}

export interface ProjectInput {
  name: string;
  description?: string | null;
  status?: ProjectStatus;
  priority?: Priority;
  repository_url?: string | null;
}

export interface TaskInput {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: Priority;
  due_date?: string | null;
  project_id?: string;
  assignee_id?: string | null;
}

export interface DocumentInput {
  title: string;
  content: string;
  project_id?: string;
}
