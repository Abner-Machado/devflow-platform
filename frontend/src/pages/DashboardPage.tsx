/** Landing screen. Every number below comes from /api/v1/dashboard. */

import { useState } from "react";
import { Link } from "react-router-dom";

import { useDashboard } from "../api/hooks";
import { ActivityChart } from "../components/ActivityChart";
import { ActivityFeed } from "../components/ActivityFeed";
import { ProjectFormModal } from "../components/ProjectFormModal";
import { IconPlus } from "../components/Icons";
import { Button, Card, CardBody, CardHeader, ProgressBar, StatusBadge } from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingCards, LoadingRows } from "../components/ui/States";
import { useAuth } from "../auth/useAuth";
import {
  formatDate,
  isOverdue,
  label,
  priorityTone,
  projectStatusTone,
  taskStatusTone,
} from "../lib/format";

function StatCard({
  label: statLabel,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card>
      <div className="stat">
        <span className="stat-label">{statLabel}</span>
        <span className="stat-value">{value}</span>
        {hint && <span className="stat-hint">{hint}</span>}
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, error, refetch } = useDashboard();
  const [creating, setCreating] = useState(false);

  const firstName = user?.full_name.split(" ")[0] ?? "there";

  if (isError) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }

  const overview = data?.overview;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Welcome back, {firstName}</h1>
          <p>Delivery status across every project you own.</p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <IconPlus />
          New project
        </Button>
      </header>

      <div className="stack">
        <div className="grid grid-stats">
          {isLoading || !overview ? (
            Array.from({ length: 4 }, (_, index) => (
              <Card key={index}>
                <div className="stat">
                  <span className="skeleton" style={{ height: 12, width: "50%" }} />
                  <span className="skeleton" style={{ height: 32, width: "35%" }} />
                </div>
              </Card>
            ))
          ) : (
            <>
              <StatCard
                label="Active projects"
                value={overview.active_projects}
                hint={`${overview.total_projects} total`}
              />
              <StatCard
                label="Open tasks"
                value={overview.open_tasks}
                hint={
                  overview.overdue_tasks > 0 ? `${overview.overdue_tasks} overdue` : "Nothing overdue"
                }
              />
              <StatCard
                label="Completed tasks"
                value={overview.completed_tasks}
                hint={`${overview.completion_rate}% completion rate`}
              />
              <StatCard
                label="Documents"
                value={overview.total_documents}
                hint="Across all projects"
              />
            </>
          )}
        </div>

        <div className="grid grid-split">
          <Card>
            <CardHeader
              title="Activity over the last 14 days"
              action={
                <Link className="subtle" to="/metrics">
                  Full metrics
                </Link>
              }
            />
            <CardBody>
              {isLoading ? (
                <LoadingRows rows={3} />
              ) : (
                <ActivityChart points={data?.activity_series ?? []} />
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Recent activity"
              action={
                <Link className="subtle" to="/activity">
                  View all
                </Link>
              }
            />
            {isLoading ? (
              <LoadingRows />
            ) : data && data.recent_activity.length > 0 ? (
              <ActivityFeed items={data.recent_activity} />
            ) : (
              <EmptyState
                title="No activity yet"
                description="Create a project or a task and it shows up here."
              />
            )}
          </Card>
        </div>

        <div className="grid grid-split">
          <Card>
            <CardHeader
              title="Active projects"
              action={
                <Link className="subtle" to="/projects">
                  All projects
                </Link>
              }
            />
            {isLoading ? (
              <LoadingRows />
            ) : data && data.active_projects.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Project</th>
                      <th>Status</th>
                      <th>Tasks</th>
                      <th style={{ width: 180 }}>Progress</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.active_projects.map((project) => (
                      <tr key={project.id}>
                        <td className="cell-strong">
                          <Link to={`/projects/${project.id}`}>{project.name}</Link>
                        </td>
                        <td>
                          <StatusBadge tone={projectStatusTone(project.status)}>
                            {label(project.status)}
                          </StatusBadge>
                        </td>
                        <td className="cell-muted">
                          {project.stats.completed_tasks}/{project.stats.total_tasks}
                        </td>
                        <td>
                          <ProgressBar value={project.stats.progress} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No active projects"
                description="Projects in planning or active status appear here."
                action={
                  <Button variant="primary" size="sm" onClick={() => setCreating(true)}>
                    Create a project
                  </Button>
                }
              />
            )}
          </Card>

          <Card>
            <CardHeader
              title="Next up"
              action={
                <Link className="subtle" to="/tasks">
                  All tasks
                </Link>
              }
            />
            {isLoading ? (
              <LoadingCards count={1} />
            ) : data && data.upcoming_tasks.length > 0 ? (
              <div className="table-wrap">
                <table className="table">
                  <tbody>
                    {data.upcoming_tasks.map((task) => (
                      <tr key={task.id}>
                        <td>
                          <div className="cell-strong">{task.title}</div>
                          <div className="subtle">{task.project_name}</div>
                        </td>
                        <td>
                          <StatusBadge tone={taskStatusTone(task.status)}>
                            {label(task.status)}
                          </StatusBadge>
                        </td>
                        <td>
                          <StatusBadge tone={priorityTone(task.priority)}>
                            {label(task.priority)}
                          </StatusBadge>
                        </td>
                        <td
                          className="cell-muted"
                          style={{
                            color: isOverdue(task.due_date, task.status)
                              ? "var(--danger)"
                              : undefined,
                          }}
                        >
                          {formatDate(task.due_date)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="Nothing open" description="Every task you own is done." />
            )}
          </Card>
        </div>
      </div>

      <ProjectFormModal open={creating} onClose={() => setCreating(false)} />
    </>
  );
}
