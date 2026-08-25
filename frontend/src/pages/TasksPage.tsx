import { useState } from "react";

import { useDeleteTask, useProjects, useTasks, useUpdateTask, type TaskFilters } from "../api/hooks";
import type { Task, TaskStatus } from "../api/types";
import { IconPlus } from "../components/Icons";
import { TaskFormModal } from "../components/TaskFormModal";
import { ConfirmDialog } from "../components/ui/Modal";
import { Button, Card, Input, Select, StatusBadge } from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingRows, Pagination } from "../components/ui/States";
import { useToast } from "../hooks/useToast";
import {
  PRIORITIES,
  TASK_STATUSES,
  formatDate,
  isOverdue,
  label,
  priorityTone,
} from "../lib/format";

export function TasksPage() {
  const [filters, setFilters] = useState<TaskFilters>({ page: 1, page_size: 20 });
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Task | null>(null);

  const { data, isLoading, isError, error, refetch, isFetching } = useTasks(filters);
  const projects = useProjects({ page_size: 100, sort_by: "name", order: "asc" });
  const updateTask = useUpdateTask();
  const deleteTask = useDeleteTask();
  const { notify } = useToast();

  function patchFilters(patch: Partial<TaskFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
  }

  async function changeStatus(task: Task, status: TaskStatus) {
    try {
      await updateTask.mutateAsync({ id: task.id, input: { status } });
      notify(status === "done" ? "Task completed." : "Task updated.", "success");
    } catch {
      notify("Could not update the task.", "error");
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    try {
      await deleteTask.mutateAsync(pendingDelete.id);
      notify("Task deleted.", "success");
    } catch {
      notify("Could not delete the task.", "error");
    } finally {
      setPendingDelete(null);
    }
  }

  const hasFilters = Boolean(
    filters.search || filters.status || filters.priority || filters.project_id || filters.overdue,
  );

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Tasks</h1>
          <p>Filter by project, status, priority or deadline.</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <IconPlus />
          New task
        </Button>
      </header>

      <Card>
        <div className="filter-bar">
          <Input
            className="search"
            type="search"
            placeholder="Search title or description"
            aria-label="Search tasks"
            value={filters.search ?? ""}
            onChange={(event) => patchFilters({ search: event.target.value })}
          />
          <Select
            aria-label="Filter by project"
            value={filters.project_id ?? ""}
            onChange={(event) => patchFilters({ project_id: event.target.value || undefined })}
          >
            <option value="">All projects</option>
            {projects.data?.items.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Filter by status"
            value={filters.status ?? ""}
            onChange={(event) => patchFilters({ status: event.target.value || undefined })}
          >
            <option value="">All statuses</option>
            {TASK_STATUSES.map((status) => (
              <option key={status} value={status}>
                {label(status)}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Filter by priority"
            value={filters.priority ?? ""}
            onChange={(event) => patchFilters({ priority: event.target.value || undefined })}
          >
            <option value="">All priorities</option>
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {label(priority)}
              </option>
            ))}
          </Select>
          <label className="row subtle" style={{ gap: "var(--space-2)" }}>
            <input
              type="checkbox"
              checked={Boolean(filters.overdue)}
              onChange={(event) => patchFilters({ overdue: event.target.checked || undefined })}
            />
            Overdue only
          </label>
          {hasFilters && (
            <Button size="sm" variant="ghost" onClick={() => setFilters({ page: 1, page_size: 20 })}>
              Clear
            </Button>
          )}
        </div>

        {isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : isLoading ? (
          <LoadingRows rows={6} />
        ) : data && data.items.length > 0 ? (
          <div className="table-wrap" style={{ opacity: isFetching ? 0.7 : 1 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Due</th>
                  <th>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <div className="cell-strong">{task.title}</div>
                      <div className="subtle">{task.project_name}</div>
                    </td>
                    <td>
                      <Select
                        aria-label={`Status of ${task.title}`}
                        value={task.status}
                        onChange={(event) =>
                          void changeStatus(task, event.target.value as TaskStatus)
                        }
                        style={{ width: 140 }}
                      >
                        {TASK_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {label(status)}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td>
                      <StatusBadge tone={priorityTone(task.priority)}>
                        {label(task.priority)}
                      </StatusBadge>
                    </td>
                    <td
                      className="cell-muted"
                      style={{
                        color: isOverdue(task.due_date, task.status) ? "var(--danger)" : undefined,
                      }}
                    >
                      {formatDate(task.due_date)}
                      {isOverdue(task.due_date, task.status) && (
                        <div className="subtle" style={{ color: "var(--danger)" }}>
                          Overdue
                        </div>
                      )}
                    </td>
                    <td>
                      <div className="cell-actions">
                        <Button size="sm" onClick={() => setEditing(task)}>
                          Edit
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setPendingDelete(task)}>
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : hasFilters ? (
          <EmptyState
            title="No tasks match these filters"
            description="Loosen a filter to see more."
            action={
              <Button size="sm" onClick={() => setFilters({ page: 1, page_size: 20 })}>
                Clear filters
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="No tasks yet"
            description="Tasks belong to a project and drive its progress bar."
            action={
              <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
                Create a task
              </Button>
            }
          />
        )}

        {data && (
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        )}
      </Card>

      <TaskFormModal
        open={creating}
        defaultProjectId={filters.project_id}
        onClose={() => setCreating(false)}
      />
      <TaskFormModal open={Boolean(editing)} task={editing} onClose={() => setEditing(null)} />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete task"
        message={`"${pendingDelete?.title}" will be removed permanently.`}
        loading={deleteTask.isPending}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
