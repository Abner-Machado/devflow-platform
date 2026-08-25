import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useDeleteProject, useDocuments, useProject, useTasks, useUpdateTask } from "../api/hooks";
import type { Task, TaskStatus } from "../api/types";
import { IconPlus } from "../components/Icons";
import { ProjectFormModal } from "../components/ProjectFormModal";
import { TaskFormModal } from "../components/TaskFormModal";
import { ConfirmDialog } from "../components/ui/Modal";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  ProgressBar,
  Select,
  StatusBadge,
} from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingRows } from "../components/ui/States";
import { useToast } from "../hooks/useToast";
import {
  TASK_STATUSES,
  formatDate,
  isOverdue,
  label,
  priorityTone,
  projectStatusTone,
} from "../lib/format";

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [creatingTask, setCreatingTask] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState(false);

  const project = useProject(projectId);
  const tasks = useTasks({ project_id: projectId, page_size: 100, sort_by: "created_at" });
  const documents = useDocuments({ project_id: projectId });
  const updateTask = useUpdateTask();
  const deleteProject = useDeleteProject();
  const { notify } = useToast();

  if (project.isError) {
    return <ErrorState error={project.error} onRetry={() => void project.refetch()} />;
  }

  if (project.isLoading || !project.data) {
    return (
      <Card>
        <LoadingRows rows={6} />
      </Card>
    );
  }

  const data = project.data;

  async function changeStatus(task: Task, status: TaskStatus) {
    try {
      await updateTask.mutateAsync({ id: task.id, input: { status } });
    } catch {
      notify("Could not update the task.", "error");
    }
  }

  async function confirmDelete() {
    try {
      await deleteProject.mutateAsync(data.id);
      notify(`Project "${data.name}" deleted.`, "success");
      navigate("/projects", { replace: true });
    } catch {
      notify("Could not delete the project.", "error");
      setDeleting(false);
    }
  }

  return (
    <>
      <header className="page-header">
        <div>
          <p className="subtle">
            <Link to="/projects">Projects</Link> / {data.name}
          </p>
          <h1>{data.name}</h1>
          <p>{data.description ?? "No description."}</p>
          <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
            <StatusBadge tone={projectStatusTone(data.status)}>{label(data.status)}</StatusBadge>
            <StatusBadge tone={priorityTone(data.priority)}>{label(data.priority)}</StatusBadge>
            <span className="subtle">Created {formatDate(data.created_at)}</span>
            {data.repository_url && (
              <a className="subtle" href={data.repository_url} target="_blank" rel="noreferrer">
                Repository
              </a>
            )}
          </div>
        </div>
        <div className="row">
          <Button onClick={() => setEditing(true)}>Edit</Button>
          <Button variant="ghost" onClick={() => setDeleting(true)}>
            Delete
          </Button>
        </div>
      </header>

      <div className="stack">
        <div className="grid grid-stats">
          <Card>
            <div className="stat">
              <span className="stat-label">Progress</span>
              <span className="stat-value">{data.stats.progress}%</span>
              <ProgressBar value={data.stats.progress} />
            </div>
          </Card>
          <Card>
            <div className="stat">
              <span className="stat-label">Open tasks</span>
              <span className="stat-value">{data.stats.open_tasks}</span>
              <span className="stat-hint">{data.stats.total_tasks} in total</span>
            </div>
          </Card>
          <Card>
            <div className="stat">
              <span className="stat-label">Completed</span>
              <span className="stat-value">{data.stats.completed_tasks}</span>
            </div>
          </Card>
          <Card>
            <div className="stat">
              <span className="stat-label">Documents</span>
              <span className="stat-value">{data.stats.document_count}</span>
              <Link className="stat-hint" to="/documentation">
                Open documentation
              </Link>
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader
            title="Tasks"
            action={
              <Button variant="primary" size="sm" onClick={() => setCreatingTask(true)}>
                <IconPlus />
                Add task
              </Button>
            }
          />
          {tasks.isError ? (
            <ErrorState error={tasks.error} onRetry={() => void tasks.refetch()} />
          ) : tasks.isLoading ? (
            <LoadingRows />
          ) : tasks.data && tasks.data.items.length > 0 ? (
            <div className="table-wrap">
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
                  {tasks.data.items.map((task) => (
                    <tr key={task.id}>
                      <td className="cell-strong">{task.title}</td>
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
                      </td>
                      <td>
                        <div className="cell-actions">
                          <Button size="sm" onClick={() => setEditingTask(task)}>
                            Edit
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No tasks in this project"
              description="Add the first one to start tracking progress."
              action={
                <Button variant="primary" size="sm" onClick={() => setCreatingTask(true)}>
                  Add task
                </Button>
              }
            />
          )}
        </Card>

        <Card>
          <CardHeader
            title="Documentation"
            action={
              <Link className="subtle" to="/documentation">
                Open editor
              </Link>
            }
          />
          {documents.isLoading ? (
            <LoadingRows rows={3} />
          ) : documents.data && documents.data.items.length > 0 ? (
            <div className="doc-list">
              {documents.data.items.map((document) => (
                <div className="doc-item" key={document.id}>
                  <span style={{ minWidth: 0 }}>
                    <span className="cell-strong">{document.title}</span>
                    <span className="subtle truncate" style={{ display: "block" }}>
                      {document.excerpt || "Empty document"}
                    </span>
                  </span>
                  <span className="subtle">{formatDate(document.updated_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <CardBody>
              <EmptyState
                title="No documents"
                description="Architecture notes and runbooks for this project live here."
              />
            </CardBody>
          )}
        </Card>
      </div>

      <ProjectFormModal open={editing} project={data} onClose={() => setEditing(false)} />
      <TaskFormModal
        open={creatingTask}
        defaultProjectId={data.id}
        onClose={() => setCreatingTask(false)}
      />
      <TaskFormModal
        open={Boolean(editingTask)}
        task={editingTask}
        onClose={() => setEditingTask(null)}
      />
      <ConfirmDialog
        open={deleting}
        title="Delete project"
        message={`"${data.name}" and all of its tasks and documents will be removed. This cannot be undone.`}
        loading={deleteProject.isPending}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleting(false)}
      />
    </>
  );
}
