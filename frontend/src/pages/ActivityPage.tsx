import { useState } from "react";

import { useActivity, useProjects } from "../api/hooks";
import type { ActivityAction } from "../api/types";
import { ActivityFeed } from "../components/ActivityFeed";
import { Card, Select } from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingRows, Pagination } from "../components/ui/States";

const ACTIONS: { value: ActivityAction | ""; label: string }[] = [
  { value: "", label: "All activity" },
  { value: "project_created", label: "Project created" },
  { value: "project_updated", label: "Project updated" },
  { value: "task_created", label: "Task created" },
  { value: "task_completed", label: "Task completed" },
  { value: "task_updated", label: "Task updated" },
  { value: "document_created", label: "Document created" },
  { value: "document_updated", label: "Document updated" },
];

export function ActivityPage() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<string>("");
  const [projectId, setProjectId] = useState("");

  const projects = useProjects({ page_size: 100, sort_by: "name", order: "asc" });
  const { data, isLoading, isError, error, refetch } = useActivity({
    page,
    action: action || undefined,
    project_id: projectId || undefined,
  });

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Activity</h1>
          <p>Written by the same code path that changes state, so it cannot drift.</p>
        </div>
      </header>

      <Card>
        <div className="filter-bar">
          <Select
            aria-label="Filter by action"
            value={action}
            onChange={(event) => {
              setAction(event.target.value);
              setPage(1);
            }}
          >
            {ACTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Select
            aria-label="Filter by project"
            value={projectId}
            onChange={(event) => {
              setProjectId(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All projects</option>
            {projects.data?.items.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
        </div>

        {isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : isLoading ? (
          <LoadingRows rows={8} />
        ) : data && data.items.length > 0 ? (
          <ActivityFeed items={data.items} />
        ) : (
          <EmptyState
            title="No activity recorded"
            description="Actions on projects, tasks and documents are logged here."
          />
        )}

        {data && (
          <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
        )}
      </Card>
    </>
  );
}
