import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const PaperRecommendations = ({
  analysisData,
  onPapersSelected,
  selectedPapers
}) => {
  const [activeCategory, setActiveCategory] = useState('core_papers');
  const [expandedPapers, setExpandedPapers] = useState(new Set());

  useEffect(() => {
    if (analysisData?.core_papers?.length > 0) {
      setActiveCategory('core_papers');
    } else if (analysisData?.method_neighbors?.length > 0) {
      setActiveCategory('method_neighbors');
    } else if (analysisData?.gap_candidates?.length > 0) {
      setActiveCategory('gap_candidates');
    } else if (analysisData?.foundation_papers?.length > 0) {
      setActiveCategory('foundation_papers');
    }
  }, [analysisData]);

  if (!analysisData) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-4">📚</div>
          <div className="font-medium">No Analysis Yet</div>
          <div className="text-sm mt-2">
            Enter a research idea to get paper recommendations
          </div>
        </div>
      </div>
    );
  }

  const categories = [
    {
      key: 'core_papers',
      label: 'Core Papers',
      description: 'Most relevant to your idea',
      icon: '🎯',
      papers: analysisData.core_papers || []
    },
    {
      key: 'method_neighbors',
      label: 'Method Papers',
      description: 'Similar approaches/methods',
      icon: '🔧',
      papers: analysisData.method_neighbors || []
    },
    {
      key: 'gap_candidates',
      label: 'Gap Candidates',
      description: 'Research gaps and opportunities',
      icon: '🔍',
      papers: analysisData.gap_candidates || []
    },
    {
      key: 'foundation_papers',
      label: 'Foundation Papers',
      description: 'Seminal works in the field',
      icon: '🏗️',
      papers: analysisData.foundation_papers || []
    }
  ];

  const activeData = categories.find(cat => cat.key === activeCategory);

  const togglePaperSelection = (paper) => {
    const isSelected = selectedPapers.some(p => p.id === paper.id);
    let newSelection;

    if (isSelected) {
      newSelection = selectedPapers.filter(p => p.id !== paper.id);
    } else {
      newSelection = [...selectedPapers, paper];
    }

    onPapersSelected(newSelection);
  };

  const togglePaperExpansion = (paperId) => {
    setExpandedPapers(prev => {
      const newSet = new Set(prev);
      if (newSet.has(paperId)) {
        newSet.delete(paperId);
      } else {
        newSet.add(paperId);
      }
      return newSet;
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Analysis Summary */}
      <div className="bg-gray-50 rounded-lg p-3 mb-4">
        <div className="text-sm font-medium text-gray-900 mb-1">
          Analysis Results
        </div>
        <div className="text-xs text-gray-600 space-y-1">
          <div>📊 {analysisData.total_papers_found} papers found</div>
          <div>⏱️ Processed in {analysisData.processing_time_ms}ms</div>
          {analysisData.summary && (
            <div className="mt-2 p-2 bg-blue-50 rounded text-xs border border-blue-200">
              💡 {analysisData.summary}
            </div>
          )}
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex space-x-1 mb-4 bg-gray-100 rounded-lg p-1">
        {categories.map(category => (
          <button
            key={category.key}
            onClick={() => setActiveCategory(category.key)}
            className={`flex-1 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
              activeCategory === category.key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <div>{category.icon} {category.label}</div>
            <div className="text-xs opacity-75 mt-1">
              ({category.papers.length})
            </div>
          </button>
        ))}
      </div>

      {/* Paper List */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {activeData?.papers.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-2xl mb-2">{activeData.icon}</div>
            <div className="font-medium">No {activeData.label}</div>
            <div className="text-xs mt-1">
              {activeData.description}
            </div>
          </div>
        ) : (
          activeData?.papers.map((paper, index) => {
            const isSelected = selectedPapers.some(p => p.id === paper.id);
            const isExpanded = expandedPapers.has(paper.id);

            return (
              <div
                key={paper.id}
                className={`border rounded-lg p-3 cursor-pointer transition-all ${
                  isSelected
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => togglePaperSelection(paper)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-500">#{index + 1}</span>
                      {isSelected && <span className="text-green-600">✅</span>}
                      <Link
                        to={`/paper/${paper.arxiv_id}`}
                        className="text-xs font-medium text-gray-900 line-clamp-2 hover:text-blue-600 hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {paper.title}
                      </Link>
                    </div>

                    <div className="mt-2 text-xs text-gray-600">
                      👥 {paper.authors?.slice(0, 3).join(', ')}
                      {paper.authors?.length > 3 && ` +${paper.authors.length - 3} more`}
                    </div>

                    {paper.categories && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {paper.categories.slice(0, 2).map(cat => (
                          <span
                            key={cat}
                            className="inline-block bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded"
                          >
                            {cat}
                          </span>
                        ))}
                      </div>
                    )}

                    {paper.explanation && (
                      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
                        <div className="font-medium text-yellow-800 mb-1">
                          💡 Why This Paper?
                        </div>
                        <div className="text-yellow-700">
                          {paper.explanation}
                        </div>
                      </div>
                    )}

                    {isExpanded && paper.abstract && (
                      <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                        <div className="font-medium mb-1">Abstract:</div>
                        <div className="text-gray-700">
                          {paper.abstract.slice(0, 300)}
                          {paper.abstract.length > 300 && '...'}
                        </div>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      togglePaperExpansion(paper.id);
                    }}
                    className="ml-2 text-gray-400 hover:text-gray-600"
                  >
                    {isExpanded ? '▼' : '▶'}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Selection Summary */}
      {selectedPapers.length > 0 && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <div className="text-sm font-medium text-green-800">
            ✅ {selectedPapers.length} papers selected for comparison
          </div>
          <div className="text-xs text-green-600 mt-1">
            Select papers from different categories for best comparison insights
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperRecommendations;