import { useState } from "react";
import { Link } from "react-router-dom";

import { useDeleteProject, useProjects, type ProjectFilters } from "../api/hooks";
import type { Project } from "../api/types";
import { IconPlus } from "../components/Icons";
import { ProjectFormModal } from "../components/ProjectFormModal";
import { ConfirmDialog } from "../components/ui/Modal";
import {
  Button,
  Card,
  CardBody,
  Input,
  ProgressBar,
  Select,
  StatusBadge,
} from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingCards, Pagination } from "../components/ui/States";
import { useToast } from "../hooks/useToast";
import {
  PRIORITIES,
  PROJECT_STATUSES,
  formatDate,
  label,
  priorityTone,
  projectStatusTone,
} from "../lib/format";

export function ProjectsPage() {
  const [filters, setFilters] = useState<ProjectFilters>({ page: 1, page_size: 12 });
  const [editing, setEditing] = useState<Project | null>(null);
  const [creating, setCreating] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null);

  const { data, isLoading, isError, error, refetch, isFetching } = useProjects(filters);
  const deleteProject = useDeleteProject();
  const { notify } = useToast();

  function patchFilters(patch: Partial<ProjectFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    try {
      await deleteProject.mutateAsync(pendingDelete.id);
      notify(`Project "${pendingDelete.name}" deleted.`, "success");
    } catch {
      notify("Could not delete the project.", "error");
    } finally {
      setPendingDelete(null);
    }
  }

  const hasFilters = Boolean(filters.search || filters.status || filters.priority);

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Projects</h1>
          <p>Progress is computed from each project&apos;s task counts.</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <IconPlus />
          New project
        </Button>
      </header>

      <Card>
        <div className="filter-bar">
          <Input
            className="search"
            type="search"
            placeholder="Search name or description"
            aria-label="Search projects"
            value={filters.search ?? ""}
            onChange={(event) => patchFilters({ search: event.target.value })}
          />
          <Select
            aria-label="Filter by status"
            value={filters.status ?? ""}
            onChange={(event) => patchFilters({ status: event.target.value || undefined })}
          >
            <option value="">All statuses</option>
            {PROJECT_STATUSES.map((status) => (
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
          <Select
            aria-label="Sort by"
            value={filters.sort_by ?? "created_at"}
            onChange={(event) => patchFilters({ sort_by: event.target.value })}
          >
            <option value="created_at">Newest first</option>
            <option value="updated_at">Recently updated</option>
            <option value="name">Name</option>
            <option value="priority">Priority</option>
          </Select>
          {hasFilters && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setFilters({ page: 1, page_size: 12 })}
            >
              Clear
            </Button>
          )}
        </div>

        <CardBody>
          {isError ? (
            <ErrorState error={error} onRetry={() => void refetch()} />
          ) : isLoading ? (
            <LoadingCards count={6} />
          ) : data && data.items.length > 0 ? (
            <div className="grid grid-cards" style={{ opacity: isFetching ? 0.7 : 1 }}>
              {data.items.map((project) => (
                <article className="card card-link" key={project.id}>
                  <div className="card-body stack">
                    <div className="row-between">
                      <Link to={`/projects/${project.id}`} style={{ fontWeight: 640 }}>
                        {project.name}
                      </Link>
                      <StatusBadge tone={projectStatusTone(project.status)}>
                        {label(project.status)}
                      </StatusBadge>
                    </div>

                    <p className="subtle" style={{ minHeight: "2.6em" }}>
                      {project.description ?? "No description."}
                    </p>

                    <ProgressBar
                      value={project.stats.progress}
                      label={`${project.stats.completed_tasks}/${project.stats.total_tasks} tasks`}
                    />

                    <div className="row wrap">
                      <StatusBadge tone={priorityTone(project.priority)}>
                        {label(project.priority)}
                      </StatusBadge>
                      <span className="subtle">{project.stats.document_count} docs</span>
                      <span className="spacer" />
                      <span className="subtle">{formatDate(project.created_at)}</span>
                    </div>

                    <div className="row">
                      <Button size="sm" onClick={() => setEditing(project)}>
                        Edit
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setPendingDelete(project)}>
                        Delete
                      </Button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : hasFilters ? (
            <EmptyState
              title="No projects match these filters"
              description="Try a different status, priority or search term."
              action={
                <Button size="sm" onClick={() => setFilters({ page: 1, page_size: 12 })}>
                  Clear filters
                </Button>
              }
            />
          ) : (
            <EmptyState
              title="No projects yet"
              description="A project groups the tasks and documentation for one piece of work."
              action={
                <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
                  Create your first project
                </Button>
              }
            />
          )}
        </CardBody>

        {data && (
          <Pagination
            page={data.page}
            pages={data.pages}
            total={data.total}
            onChange={(page) => setFilters((current) => ({ ...current, page }))}
          />
        )}
      </Card>

      <ProjectFormModal open={creating} onClose={() => setCreating(false)} />
      <ProjectFormModal
        open={Boolean(editing)}
        project={editing}
        onClose={() => setEditing(null)}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete project"
        message={`"${pendingDelete?.name}" and all of its tasks and documents will be removed. This cannot be undone.`}
        loading={deleteProject.isPending}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
