/**
 * Activity over time, drawn as inline SVG.
 *
 * A hand-rolled chart instead of a charting library: the shape is two series of
 * daily counters, and the whole thing is ~60 lines that inherit theme tokens.
 */

import type { ActivityPoint } from "../api/types";

interface Props {
  points: ActivityPoint[];
  height?: number;
}

const PADDING = { top: 12, right: 8, bottom: 22, left: 26 };

export function ActivityChart({ points, height = 200 }: Props) {
  if (points.length === 0) {
    return <p className="muted">No activity recorded yet.</p>;
  }

  const width = 640; // viewBox units; the SVG scales to its container
  const innerWidth = width - PADDING.left - PADDING.right;
  const innerHeight = height - PADDING.top - PADDING.bottom;
  const maxValue = Math.max(1, ...points.map((point) => Math.max(point.created, point.completed)));

  const xFor = (index: number) =>
    PADDING.left + (points.length === 1 ? innerWidth / 2 : (index / (points.length - 1)) * innerWidth);
  const yFor = (value: number) => PADDING.top + innerHeight - (value / maxValue) * innerHeight;

  const line = (key: "created" | "completed") =>
    points.map((point, index) => `${index === 0 ? "M" : "L"}${xFor(index)},${yFor(point[key])}`).join(" ");

  const area = `${line("created")} L${xFor(points.length - 1)},${PADDING.top + innerHeight} L${xFor(0)},${
    PADDING.top + innerHeight
  } Z`;

  const ticks = [0, Math.round(maxValue / 2), maxValue];
  const labelEvery = Math.max(1, Math.ceil(points.length / 7));

  return (
    <figure>
      <svg
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Activity over the last ${points.length} days`}
      >
        <g className="chart-grid">
          {ticks.map((tick) => (
            <line key={tick} x1={PADDING.left} x2={width - PADDING.right} y1={yFor(tick)} y2={yFor(tick)} />
          ))}
        </g>

        <g className="chart-axis">
          {ticks.map((tick) => (
            <text key={tick} x={4} y={yFor(tick) + 3}>
              {tick}
            </text>
          ))}
          {points.map((point, index) =>
            index % labelEvery === 0 ? (
              <text key={point.day} x={xFor(index)} y={height - 6} textAnchor="middle">
                {point.day.slice(5)}
              </text>
            ) : null,
          )}
        </g>

        <path d={area} fill="var(--brand-500)" opacity="0.12" />
        <path d={line("created")} fill="none" stroke="var(--brand-500)" strokeWidth="2" />
        <path
          d={line("completed")}
          fill="none"
          stroke="var(--success)"
          strokeWidth="2"
          strokeDasharray="4 3"
        />
      </svg>

      <figcaption className="chart-legend">
        <span>
          <span className="chart-swatch" style={{ background: "var(--brand-500)" }} />
          Created
        </span>
        <span>
          <span className="chart-swatch" style={{ background: "var(--success)" }} />
          Completed
        </span>
      </figcaption>
    </figure>
  );
}

export function BarList({
  items,
}: {
  items: { label: string; count: number; tone?: string }[];
}) {
  const max = Math.max(1, ...items.map((item) => item.count));
  return (
    <div className="bars">
      {items.map((item) => (
        <div className="bar-row" key={item.label}>
          <span className="muted">{item.label}</span>
          <span className="bar-track">
            <span
              className="bar-fill"
              style={{
                width: `${(item.count / max) * 100}%`,
                background: item.tone ?? "var(--brand-500)",
              }}
            />
          </span>
          <span className="bar-count">{item.count}</span>
        </div>
      ))}
    </div>
  );
}
