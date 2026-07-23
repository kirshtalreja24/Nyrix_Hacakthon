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
    <div className="space-y-6">
      {results.map((r, i) => (
        <ResultCard key={i} result={r} index={i} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function ResultCard({ result, index }) {
  const ChartComponent = CHART_COMPONENTS[result.chart_type] || EmptyState;

  const props = {
    data: result.chart_data,
    insight: result.insight,
    title: result.question,
  };

  return (
    <div style={{ animationDelay: `${index * 80}ms` }}>
      {/* Question chip */}
      <div className="flex items-start gap-3 mb-3">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-canvas border border-border
          flex items-center justify-center text-xs font-mono text-text-muted">
          {index + 1}
        </div>
        <div>
          <p className="text-sm font-sans font-medium text-text-primary">{result.question}</p>
          <p className="text-xs font-mono text-text-muted mt-0.5">
            {result.chart_type_label} · {result.source === 'csv_duckdb' ? 'CSV Data' : 'PostgreSQL'}
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="ml-10">
        <ChartComponent {...props} />
      </div>
    </div>
  );
}
