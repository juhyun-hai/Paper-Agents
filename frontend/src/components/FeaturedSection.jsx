import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PaperCard from './PaperCard.jsx';
import { PaperCardSkeleton } from './Skeleton.jsx';
import { API_BASE } from '../api/client';

/**
 * Featured papers section — shows today's curated top picks (and optionally
 * the HAI-Lab-relevant subset on a separate row).
 *
 * Props:
 *   endpoint:  API path under API_BASE (e.g. '/featured/today', '/hai/papers').
 *   title:     Section title (e.g. "Today's Top 25").
 *   subtitle:  Optional subtitle text.
 *   accent:    Tailwind color name for accent bar ('orange', 'indigo', etc).
 *   count:     How many papers to show (default 6).
 */
export default function FeaturedSection({
  endpoint,
  title,
  subtitle,
  accent = 'blue',
  count = 6,
  badge = null,
  viewAllPath = '/trending',
}) {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}${endpoint}?limit=${count}`)
      .then((r) => r.json())
      .then((d) => {
        setPapers(d.papers || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [endpoint, count]);

  if (!loading && papers.length === 0) return null;

  const accentBg = {
    blue: 'bg-blue-600 hover:bg-blue-700',
    orange: 'bg-orange-500 hover:bg-orange-600',
    indigo: 'bg-indigo-600 hover:bg-indigo-700',
  }[accent] || 'bg-blue-600 hover:bg-blue-700';

  return (
    <section className="max-w-5xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h2>
            {badge && (
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${accentBg} text-white`}>
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
        </div>
        <Link
          to={viewAllPath}
          className={`text-sm ${accentBg} text-white px-4 py-2 rounded-lg transition-colors`}
        >
          View All →
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading
          ? Array.from({ length: count }).map((_, i) => <PaperCardSkeleton key={i} />)
          : papers.slice(0, count).map((p) => (
              <PaperCard key={p.arxiv_id || p.id} paper={p} />
            ))}
      </div>
    </section>
  );
}
