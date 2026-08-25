import { useState } from "react";

import { useMetrics } from "../api/hooks";
import { ActivityChart, BarList } from "../components/ActivityChart";
import { Card, CardBody, CardHeader, ProgressBar, Select } from "../components/ui/Primitives";
import { EmptyState, ErrorState, LoadingRows } from "../components/ui/States";
import { label } from "../lib/format";

const WINDOWS = [7, 14, 30, 90];

const STATUS_COLOURS: Record<string, string> = {
  todo: "var(--text-subtle)",
  in_progress: "var(--info)",
  in_review: "var(--brand-500)",
  done: "var(--success)",
};

const PRIORITY_COLOURS: Record<string, string> = {
  low: "var(--text-subtle)",
  medium: "var(--info)",
  high: "var(--warning)",
  critical: "var(--danger)",
};

export function MetricsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading, isError, error, refetch } = useMetrics(days);

  if (isError) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const overview = data?.overview;
  const hasData = Boolean(overview && overview.total_tasks + overview.total_projects > 0);

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Metrics</h1>
          <p>Aggregated from your own rows. No estimates, no sample data.</p>
        </div>
        <Select
          aria-label="Time window"
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
          style={{ width: 160 }}
        >
          {WINDOWS.map((window) => (
            <option key={window} value={window}>
              Last {window} days
            </option>
          ))}
        </Select>
      </header>

      {isLoading || !overview ? (
        <Card>
          <LoadingRows rows={8} />
        </Card>
      ) : !hasData ? (
        <Card>
          <EmptyState
            title="Nothing to measure yet"
            description="Create a project and a few tasks; the numbers here follow automatically."
          />
        </Card>
      ) : (
        <div className="stack">
          <div className="grid grid-stats">
            <Card>
              <div className="stat">
                <span className="stat-label">Completion rate</span>
                <span className="stat-value">{overview.completion_rate}%</span>
                <ProgressBar value={overview.completion_rate} />
              </div>
            </Card>
            <Card>
              <div className="stat">
                <span className="stat-label">Open tasks</span>
                <span className="stat-value">{overview.open_tasks}</span>
                <span className="stat-hint">{overview.overdue_tasks} past their due date</span>
              </div>
            </Card>
            <Card>
              <div className="stat">
                <span className="stat-label">Completed tasks</span>
                <span className="stat-value">{overview.completed_tasks}</span>
                <span className="stat-hint">of {overview.total_tasks} total</span>
              </div>
            </Card>
            <Card>
              <div className="stat">
                <span className="stat-label">Projects</span>
                <span className="stat-value">{overview.active_projects}</span>
                <span className="stat-hint">
                  {overview.completed_projects} completed - {overview.total_projects} total
                </span>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader title={`Activity over the last ${days} days`} />
            <CardBody>
              <ActivityChart points={data?.activity_series ?? []} height={240} />
            </CardBody>
          </Card>

          <div className="grid grid-split">
            <Card>
              <CardHeader title="Tasks by status" />
              <CardBody>
                <BarList
                  items={(data?.tasks_by_status ?? []).map((slice) => ({
                    label: label(slice.status),
                    count: slice.count,
                    tone: STATUS_COLOURS[slice.status],
                  }))}
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Tasks by priority" />
              <CardBody>
                <BarList
                  items={(data?.tasks_by_priority ?? []).map((slice) => ({
                    label: label(slice.priority),
                    count: slice.count,
                    tone: PRIORITY_COLOURS[slice.priority],
                  }))}
                />
              </CardBody>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}
