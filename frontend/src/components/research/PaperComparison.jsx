import React, { useState } from 'react';
import { comparePapers } from '../../api/research';

const PaperComparison = ({
  selectedPapers,
  onComparisonComplete,
  comparisonData,
  isLoading,
  setIsLoading
}) => {
  const [focusAspects, setFocusAspects] = useState(['method', 'task', 'results']);
  const [error, setError] = useState('');

  const availableAspects = [
    { key: 'method', label: 'Method', icon: '🔧' },
    { key: 'task', label: 'Task/Problem', icon: '🎯' },
    { key: 'results', label: 'Results', icon: '📊' },
    { key: 'dataset', label: 'Dataset', icon: '📚' },
    { key: 'evaluation', label: 'Evaluation', icon: '⚖️' },
    { key: 'limitations', label: 'Limitations', icon: '⚠️' }
  ];

  const handleCompare = async () => {
    if (selectedPapers.length < 2) return;

    setIsLoading(true);
    setError('');

    try {
      const paperIds = selectedPapers.map(paper => paper.id);
      const result = await comparePapers({
        paper_ids: paperIds,
        focus_aspects: focusAspects
      });

      onComparisonComplete(result);
    } catch (err) {
      setError(err.message || 'Failed to compare papers');
      console.error('Comparison error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAspect = (aspect) => {
    setFocusAspects(prev =>
      prev.includes(aspect)
        ? prev.filter(a => a !== aspect)
        : [...prev, aspect]
    );
  };

  if (selectedPapers.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-4">⚖️</div>
          <div className="font-medium">No Papers Selected</div>
          <div className="text-sm mt-2">
            Select 2+ papers from recommendations to enable comparison
          </div>
        </div>
      </div>
    );
  }

  if (selectedPapers.length === 1) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-4">⚖️</div>
          <div className="font-medium">Need More Papers</div>
          <div className="text-sm mt-2">
            Select at least 2 papers to compare
          </div>
          <div className="text-xs text-gray-400 mt-1">
            Currently selected: {selectedPapers.length}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Selected Papers Summary */}
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-900 mb-2">
          Selected Papers ({selectedPapers.length})
        </div>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {selectedPapers.map((paper, index) => (
            <div
              key={paper.id}
              className="bg-gray-50 rounded p-2 text-xs border"
            >
              <div className="font-medium text-gray-900">
                #{index + 1}: {paper.title.slice(0, 60)}
                {paper.title.length > 60 && '...'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Comparison Aspects */}
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-900 mb-2">
          Focus Aspects
        </div>
        <div className="grid grid-cols-2 gap-2">
          {availableAspects.map(aspect => (
            <label
              key={aspect.key}
              className="flex items-center space-x-2 text-xs cursor-pointer"
            >
              <input
                type="checkbox"
                checked={focusAspects.includes(aspect.key)}
                onChange={() => toggleAspect(aspect.key)}
                className="w-3 h-3 text-purple-600 rounded focus:ring-purple-500"
              />
              <span>{aspect.icon} {aspect.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Compare Button */}
      <button
        onClick={handleCompare}
        disabled={selectedPapers.length < 2 || focusAspects.length === 0 || isLoading}
        className="w-full bg-purple-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm mb-4"
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
            Comparing...
          </div>
        ) : (
          `⚖️ Compare ${selectedPapers.length} Papers`
        )}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      {/* Comparison Results */}
      <div className="flex-1 overflow-y-auto">
        {!comparisonData ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-2xl mb-2">📊</div>
            <div className="font-medium">Ready to Compare</div>
            <div className="text-xs mt-1">
              Click the compare button to analyze differences and similarities
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Processing Time */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-600">
                ⏱️ Analyzed in {comparisonData.processing_time_ms}ms
              </div>
            </div>

            {/* Paper-by-Paper Comparison */}
            {comparisonData.comparison && comparisonData.comparison.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  📋 Individual Analysis
                </div>
                <div className="space-y-3">
                  {comparisonData.comparison.map((paper, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-3">
                      <div className="font-medium text-sm text-gray-900 mb-2">
                        Paper #{index + 1}: {paper.title?.slice(0, 50)}...
                      </div>

                      {paper.strengths && (
                        <div className="mb-2">
                          <div className="text-xs font-medium text-green-700 mb-1">
                            ✅ Strengths:
                          </div>
                          <div className="text-xs text-gray-700 bg-green-50 p-2 rounded">
                            {paper.strengths}
                          </div>
                        </div>
                      )}

                      {paper.limitations && (
                        <div className="mb-2">
                          <div className="text-xs font-medium text-red-700 mb-1">
                            ⚠️ Limitations:
                          </div>
                          <div className="text-xs text-gray-700 bg-red-50 p-2 rounded">
                            {paper.limitations}
                          </div>
                        </div>
                      )}

                      {paper.key_contributions && (
                        <div>
                          <div className="text-xs font-medium text-blue-700 mb-1">
                            🎯 Key Contributions:
                          </div>
                          <div className="text-xs text-gray-700 bg-blue-50 p-2 rounded">
                            {paper.key_contributions}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Common Themes */}
            {comparisonData.common_themes && comparisonData.common_themes.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  🤝 Common Themes
                </div>
                <div className="space-y-2">
                  {comparisonData.common_themes.map((theme, index) => (
                    <div key={index} className="bg-blue-50 border border-blue-200 rounded p-3">
                      <div className="text-xs text-blue-800">
                        {theme}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Key Differences */}
            {comparisonData.key_differences && comparisonData.key_differences.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  ⚡ Key Differences
                </div>
                <div className="space-y-2">
                  {comparisonData.key_differences.map((difference, index) => (
                    <div key={index} className="bg-yellow-50 border border-yellow-200 rounded p-3">
                      <div className="text-xs text-yellow-800">
                        {difference}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Synthesis */}
            {comparisonData.synthesis && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  🧠 Overall Analysis
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded p-3">
                  <div className="text-xs text-gray-700">
                    {comparisonData.synthesis}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PaperComparison;