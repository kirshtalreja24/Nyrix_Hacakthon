import { useScrollEntry } from '../lib/hooks';

export default function EmptyState({ message }) {
  const ref = useScrollEntry();
  return (
    <div ref={ref} className="scroll-entry">
      <div className="bg-surface border border-border rounded-card p-12 text-center">
        <div className="w-10 h-10 rounded-card bg-canvas border border-border mx-auto mb-4 flex items-center justify-center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-text-muted">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
        </div>
        <p className="text-sm text-text-secondary">
          {message || 'No results found. Try rephrasing your question.'}
        </p>
      </div>
    </div>
  );
}

