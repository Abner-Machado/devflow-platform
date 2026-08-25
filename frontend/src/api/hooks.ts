/**
 * React Query bindings.
 *
 * Every mutation invalidates the query families whose numbers it can change, so
 * the dashboard and the metric cards never show a stale count after an edit.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  Activity,
  DashboardResponse,
  DocumentDetail,
  DocumentInput,
  DocumentSummary,
  MetricsResponse,
  Page,
  Project,
  ProjectInput,
  Task,
  TaskInput,
} from "./types";

export const queryKeys = {
  dashboard: ["dashboard"] as const,
  metrics: ["metrics"] as const,
  projects: ["projects"] as const,
  project: (id: string) => ["projects", id] as const,
  tasks: ["tasks"] as const,
  documents: ["documents"] as const,
  document: (id: string) => ["documents", id] as const,
  activity: ["activity"] as const,
};

/** Anything derived from the aggregate counters. */
const DERIVED_KEYS = [queryKeys.dashboard, queryKeys.metrics, queryKeys.activity];

function useInvalidate() {
  const queryClient = useQueryClient();
  return (extra: readonly (readonly string[])[] = []) => {
    for (const key of [...DERIVED_KEYS, ...extra]) {
      void queryClient.invalidateQueries({ queryKey: key });
    }
  };
}

export type ProjectFilters = {
  page?: number;
  page_size?: number;
  status?: string;
  priority?: string;
  search?: string;
  sort_by?: string;
  order?: string;
};

export type TaskFilters = ProjectFilters & {
  project_id?: string;
  assignee_id?: string;
  overdue?: boolean;
};

export function useDashboard() {
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: () => api.get<DashboardResponse>("/dashboard"),
  });
}

export function useMetrics(days: number) {
  return useQuery({
    queryKey: [...queryKeys.metrics, days],
    queryFn: () => api.get<MetricsResponse>("/metrics", { days }),
  });
}

export function useProjects(filters: ProjectFilters = {}) {
  return useQuery({
    queryKey: [...queryKeys.projects, filters],
    queryFn: () => api.get<Page<Project>>("/projects", filters),
  });
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.project(id ?? ""),
    queryFn: () => api.get<Project>(`/projects/${id}`),
    enabled: Boolean(id),
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: ProjectInput) => api.post<Project>("/projects", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      invalidate();
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<ProjectInput> }) =>
      api.patch<Project>(`/projects/${id}`, input),
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(project.id) });
      invalidate();
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete<{ message: string }>(`/projects/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
      // Cascade: the project took its tasks and documents with it.
      invalidate([queryKeys.tasks, queryKeys.documents]);
    },
  });
}

export function useTasks(filters: TaskFilters = {}) {
  return useQuery({
    queryKey: [...queryKeys.tasks, filters],
    queryFn: () => api.get<Page<Task>>("/tasks", filters),
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: TaskInput) => api.post<Task>("/tasks", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
      invalidate([queryKeys.projects]);
    },
  });
}

export function useUpdateTask() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<TaskInput> }) =>
      api.patch<Task>(`/tasks/${id}`, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
      invalidate([queryKeys.projects]);
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete<{ message: string }>(`/tasks/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
      invalidate([queryKeys.projects]);
    },
  });
}

export function useDocuments(filters: { project_id?: string; search?: string; page?: number } = {}) {
  return useQuery({
    queryKey: [...queryKeys.documents, filters],
    queryFn: () => api.get<Page<DocumentSummary>>("/documents", filters),
  });
}

export function useDocument(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.document(id ?? ""),
    queryFn: () => api.get<DocumentDetail>(`/documents/${id}`),
    enabled: Boolean(id),
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (input: DocumentInput) => api.post<DocumentDetail>("/documents", input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents });
      invalidate([queryKeys.projects]);
    },
  });
}

export function useUpdateDocument() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: Partial<DocumentInput> }) =>
      api.patch<DocumentDetail>(`/documents/${id}`, input),
    onSuccess: (document) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents });
      void queryClient.invalidateQueries({ queryKey: queryKeys.document(document.id) });
      invalidate();
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  const invalidate = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => api.delete<{ message: string }>(`/documents/${id}`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.documents });
      invalidate([queryKeys.projects]);
    },
  });
}

export function useActivity(filters: { page?: number; project_id?: string; action?: string } = {}) {
  return useQuery({
    queryKey: [...queryKeys.activity, filters],
    queryFn: () => api.get<Page<Activity>>("/activity", filters),
  });
}
