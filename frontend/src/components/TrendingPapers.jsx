import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE } from '../api/client';

const TrendingPapers = () => {
  const [trendingPapers, setTrendingPapers] = useState([]);
  const [weeklyPapers, setWeeklyPapers] = useState([]);
  const [stats, setStats] = useState({});
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('today'); // 'today' or 'week'
  const [error, setError] = useState('');

  useEffect(() => {
    loadTrendingData();
  }, []);

  const loadTrendingData = async () => {
    setLoading(true);
    setError('');

    try {
      // Load all trending data in parallel
      const [todayRes, weekRes, statsRes, sourcesRes] = await Promise.all([
        fetch(`${API_BASE}/trending/today?limit=30`),
        fetch(`${API_BASE}/trending/week?limit=50`),
        fetch(`${API_BASE}/trending/stats`),
        fetch(`${API_BASE}/trending/sources`)
      ]);

      if (todayRes.ok) {
        const todayData = await todayRes.json();
        setTrendingPapers(todayData.trending_papers || []);
      }

      if (weekRes.ok) {
        const weekData = await weekRes.json();
        setWeeklyPapers(weekData.weekly_trending || []);
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }

      if (sourcesRes.ok) {
        const sourcesData = await sourcesRes.json();
        setSources(sourcesData.source_statistics || []);
      }

    } catch (err) {
      console.error('Failed to load trending data:', err);
      setError('Failed to load trending papers');
    } finally {
      setLoading(false);
    }
  };

  const formatSource = (source) => {
    const sourceMap = {
      'huggingface': { name: '🤗 Hugging Face', color: 'bg-yellow-100 text-yellow-800' },
      'arxiv': { name: '📚 arXiv', color: 'bg-blue-100 text-blue-800' },
      'paperswithcode': { name: '💻 Papers with Code', color: 'bg-green-100 text-green-800' },
      'reddit_ml': { name: '🗨️ Reddit ML', color: 'bg-orange-100 text-orange-800' },
      'social_media': { name: '📱 Social', color: 'bg-purple-100 text-purple-800' }
    };
    return sourceMap[source] || { name: source, color: 'bg-gray-100 text-gray-800' };
  };

  const getSourceUrl = (source, arxivId) => {
    const urlMap = {
      'huggingface': `https://huggingface.co/papers/${arxivId}`,
      'arxiv': `https://arxiv.org/abs/${arxivId}`,
      'paperswithcode': `https://paperswithcode.com/search?q=${arxivId}`,
      'reddit_ml': `https://www.reddit.com/r/MachineLearning/search/?q=${arxivId}`,
      'social_media': `https://twitter.com/search?q=${arxivId}`
    };
    return urlMap[source] || null;
  };

  const getTrendingIcon = (rank) => {
    if (rank <= 3) return '🔥';
    if (rank <= 10) return '⭐';
    if (rank <= 20) return '📈';
    return '📄';
  };

  const truncateText = (text, maxLength = 100) => {
    if (!text) return '';
    return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
  };

  const currentPapers = view === 'today' ? trendingPapers : weeklyPapers;

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 rounded w-1/3 mb-6"></div>
          <div className="space-y-4">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            🔥 Trending Papers
          </h1>
          <button
            onClick={loadTrendingData}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 Refresh
          </button>
        </div>
        <p className="text-gray-600">
          Discover the hottest papers in AI/ML research, curated from multiple sources
        </p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-blue-600 mb-1">
            {stats.today_count || 0}
          </div>
          <div className="text-sm text-gray-600">Today's Trending</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-green-600 mb-1">
            {stats.week_unique || 0}
          </div>
          <div className="text-sm text-gray-600">This Week</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-purple-600 mb-1">
            {stats.multi_source_today || 0}
          </div>
          <div className="text-sm text-gray-600">Multi-Source</div>
        </div>
        <div className="bg-white rounded-lg border p-4">
          <div className="text-2xl font-bold text-orange-600 mb-1">
            {sources.length}
          </div>
          <div className="text-sm text-gray-600">Active Sources</div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setView('today')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              view === 'today'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🔥 Today ({trendingPapers.length})
          </button>
          <button
            onClick={() => setView('week')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              view === 'week'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📈 This Week ({weeklyPapers.length})
          </button>
        </div>

        {/* Source Legend */}
        <div className="flex flex-wrap gap-2">
          {sources.slice(0, 5).map((source, index) => {
            const sourceInfo = formatSource(source.source);
            return (
              <span
                key={index}
                className={`px-2 py-1 rounded text-xs font-medium ${sourceInfo.color}`}
              >
                {sourceInfo.name} ({source.count})
              </span>
            );
          })}
        </div>
      </div>

      {/* Trending Papers List */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {currentPapers.map((paper, index) => (
          <div
            key={paper.arxiv_id}
            className="bg-white rounded-lg border hover:shadow-md transition-shadow"
          >
            <div className="p-6">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-start space-x-3 flex-1">
                  {/* Rank & Icon */}
                  <div className="flex flex-col items-center space-y-1">
                    <span className="text-2xl">
                      {getTrendingIcon(paper.trending_rank || paper.best_rank || index + 1)}
                    </span>
                    <span className="text-sm text-gray-500 font-mono">
                      #{paper.trending_rank || paper.best_rank || index + 1}
                    </span>
                  </div>

                  {/* Paper Info */}
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/paper/${paper.arxiv_id}`}
                      className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition-colors block mb-2"
                    >
                      {paper.title}
                    </Link>

                    {/* Authors */}
                    {paper.authors && paper.authors.length > 0 && (
                      <div className="text-sm text-gray-600 mb-2">
                        by {paper.authors.slice(0, 3).join(', ')}
                        {paper.authors.length > 3 && ` +${paper.authors.length - 3} more`}
                      </div>
                    )}

                    {/* Abstract Preview */}
                    {paper.abstract && (
                      <p className="text-sm text-gray-700 mb-3">
                        {truncateText(paper.abstract, 200)}
                      </p>
                    )}

                    {/* Categories & Metadata */}
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      {paper.categories && paper.categories.slice(0, 3).map((category, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-md"
                        >
                          {category}
                        </span>
                      ))}
                      {paper.published_date && (
                        <span className="text-xs text-gray-500">
                          📅 {new Date(paper.published_date).toLocaleDateString()}
                        </span>
                      )}
                      {paper.citation_count > 0 && (
                        <span className="text-xs text-gray-500">
                          📄 {paper.citation_count} citations
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Trending Score & Sources */}
                <div className="flex flex-col items-end space-y-2 ml-4">
                  {/* Score */}
                  <div className="text-right">
                    <div className="text-lg font-bold text-orange-600">
                      {(paper.final_score || paper.weekly_score || paper.trending_score || 0).toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500">trending score</div>
                  </div>

                  {/* Sources */}
                  <div className="flex flex-wrap gap-1 justify-end">
                    {(paper.sources || []).slice(0, 3).map((source, idx) => {
                      const sourceInfo = formatSource(source);
                      const sourceUrl = getSourceUrl(source, paper.arxiv_id);
                      return sourceUrl ? (
                        <a
                          key={idx}
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`px-2 py-1 rounded text-xs font-medium hover:opacity-80 transition-opacity cursor-pointer ${sourceInfo.color}`}
                          title={`View on ${sourceInfo.name}`}
                        >
                          {sourceInfo.name.split(' ')[0]} {/* Just the emoji */}
                        </a>
                      ) : (
                        <span
                          key={idx}
                          className={`px-2 py-1 rounded text-xs font-medium ${sourceInfo.color}`}
                        >
                          {sourceInfo.name.split(' ')[0]} {/* Just the emoji */}
                        </span>
                      );
                    })}
                  </div>

                  {/* Multi-source Bonus */}
                  {paper.multi_source_bonus > 0 && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      🔗 Multi-source +{paper.multi_source_bonus}
                    </span>
                  )}

                  {/* Days Trending (Weekly View) */}
                  {paper.days_trending > 1 && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      📈 {paper.days_trending} days
                    </span>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/paper/${paper.arxiv_id}`}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    📖 View Details
                  </Link>
                  <a
                    href={`https://arxiv.org/abs/${paper.arxiv_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-600 hover:text-gray-800 text-sm font-medium"
                  >
                    📄 arXiv
                  </a>
                  {paper.pdf_url && (
                    <a
                      href={paper.pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-red-600 hover:text-red-800 text-sm font-medium"
                    >
                      📋 PDF
                    </a>
                  )}

                  {/* External Source Links */}
                  {(paper.sources || []).map((source, idx) => {
                    const sourceUrl = getSourceUrl(source, paper.arxiv_id);
                    const sourceInfo = formatSource(source);
                    if (!sourceUrl || source === 'arxiv') return null; // Skip arxiv since we already have it

                    return (
                      <a
                        key={idx}
                        href={sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-purple-600 hover:text-purple-800 text-sm font-medium"
                        title={`View on ${sourceInfo.name}`}
                      >
                        {sourceInfo.name}
                      </a>
                    );
                  })}
                </div>

                <div className="text-xs text-gray-500">
                  arXiv:{paper.arxiv_id}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {currentPapers.length === 0 && !loading && (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">📊</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Trending Papers Found
          </h3>
          <p className="text-gray-600 mb-4">
            Run the trending collector to discover today's hottest papers
          </p>
          <button
            onClick={loadTrendingData}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh Data
          </button>
        </div>
      )}
    </div>
  );
};

export default TrendingPapers;