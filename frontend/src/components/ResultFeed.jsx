import { useRef, useEffect } from 'react';
import KpiCard from './KpiCard';
import BarChart from './BarChart';
import PieChart from './PieChart';
import LineChart from './LineChart';
import RankedTable from './RankedTable';
import GeoHeatmap from './GeoHeatmap';
import EmptyState from './EmptyState';

const CHART_COMPONENTS = {
  kpi_scorecard: KpiCard,
  bar: BarChart,
  pie: PieChart,
  line: LineChart,
  ranked_table: RankedTable,
  geo_heatmap: GeoHeatmap,
  empty: EmptyState,
};

export default function ResultFeed({ results }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [results.length]);

  if (results.length === 0) return null;

  return (
    <div className="relative">
      {/* Vertical conversation thread line */}
      <div className="absolute left-[21px] top-0 bottom-0 w-px bg-border/60" />

      <div className="space-y-0">
        {results.map((r, i) => (
          <ResultCard
            key={i}
            result={r}
            index={i}
            isFollowUp={i > 0}
          />
        ))}
      </div>
      <div ref={bottomRef} />
    </div>
  );
}

function ResultCard({ result, index, isFollowUp }) {
  const ChartComponent = CHART_COMPONENTS[result.chart_type] || EmptyState;

  const props = {
    data: result.chart_data,
    insight: result.insight,
    title: result.question,
  };

  const sourceLabel = result.source === 'cross_source' ? 'Cross-Source'
    : result.source === 'csv_duckdb' ? 'CSV Data'
    : 'PostgreSQL';

  return (
    <div
      className="relative pl-12 pb-8 animate-fade-in"
      style={{ animationDelay: `${index * 100}ms` }}
    >
      {/* Thread dot */}
      <div className="absolute left-4 top-1 w-4 h-4 rounded-full bg-surface border-2 border-text-primary/20 z-10
        flex items-center justify-center">
        <div className="w-1.5 h-1.5 rounded-full bg-text-primary/40" />
      </div>

      {/* User question bubble */}
      <div className="mb-3">
        <div className="inline-block px-4 py-2.5 bg-canvas border border-border rounded-card
          max-w-[85%] shadow-subtle">
          {isFollowUp && (
            <span className="text-[10px] font-mono text-text-muted block mb-0.5">
              follow-up
            </span>
          )}
          <p className="text-sm font-sans text-text-primary leading-snug">
            {result.question}
          </p>
        </div>
      </div>

      {/* Assistant answer card */}
      <div className="animate-fade-up">
        {/* Chart type badge */}
        <div className="flex items-center gap-2 mb-2 ml-1">
          <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5
            rounded-card bg-pale-blue text-pale-blue-text">
            {result.chart_type_label}
          </span>
          {result.source === 'cross_source' && (
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5
              rounded-card bg-pale-yellow text-pale-yellow-text">
              Cross-Source
            </span>
          )}
          <span className="text-[10px] font-mono text-text-muted">
            · {sourceLabel}
          </span>
        </div>

        {/* Chart */}
        <div className="bg-surface border border-border rounded-card p-5 shadow-subtle">
          <ChartComponent {...props} />
        </div>
      </div>
    </div>
  );
}
