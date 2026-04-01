import React, { useState } from 'react';
import { generateResearchQuestions } from '../../api/research';

const ResearchQuestions = ({
  selectedPapers,
  analysisData,
  onQuestionsComplete,
  questionsData,
  isLoading,
  setIsLoading
}) => {
  const [questionTypes, setQuestionTypes] = useState(['gap', 'extension', 'methodology']);
  const [error, setError] = useState('');

  const availableTypes = [
    { key: 'gap', label: 'Research Gaps', icon: '🔍', description: 'Identify unexplored areas' },
    { key: 'extension', label: 'Extensions', icon: '🚀', description: 'Natural next steps' },
    { key: 'methodology', label: 'Methodology', icon: '⚙️', description: 'Method improvements' },
    { key: 'application', label: 'Applications', icon: '🎯', description: 'New use cases' },
    { key: 'evaluation', label: 'Evaluation', icon: '📊', description: 'Better benchmarks' },
    { key: 'combination', label: 'Combinations', icon: '🔗', description: 'Cross-pollination ideas' }
  ];

  const handleGenerateQuestions = async () => {
    if (selectedPapers.length === 0) return;

    setIsLoading(true);
    setError('');

    try {
      const paperIds = selectedPapers.map(paper => paper.id);
      const result = await generateResearchQuestions({
        paper_ids: paperIds,
        question_types: questionTypes
      });

      onQuestionsComplete(result);
    } catch (err) {
      setError(err.message || 'Failed to generate research questions');
      console.error('Question generation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleQuestionType = (type) => {
    setQuestionTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  if (selectedPapers.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <div className="text-center">
          <div className="text-4xl mb-4">❓</div>
          <div className="font-medium">No Papers Selected</div>
          <div className="text-sm mt-2">
            Select papers to generate targeted research questions
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Question Type Selection */}
      <div className="mb-4">
        <div className="text-sm font-medium text-gray-900 mb-3">
          Question Types
        </div>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {availableTypes.map(type => (
            <label
              key={type.key}
              className="flex items-start space-x-3 text-xs cursor-pointer hover:bg-gray-50 p-2 rounded"
            >
              <input
                type="checkbox"
                checked={questionTypes.includes(type.key)}
                onChange={() => toggleQuestionType(type.key)}
                className="w-3 h-3 text-orange-600 rounded focus:ring-orange-500 mt-1"
              />
              <div>
                <div className="font-medium">{type.icon} {type.label}</div>
                <div className="text-gray-600 text-xs">{type.description}</div>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Generate Button */}
      <button
        onClick={handleGenerateQuestions}
        disabled={selectedPapers.length === 0 || questionTypes.length === 0 || isLoading}
        className="w-full bg-orange-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm mb-4"
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
            Generating...
          </div>
        ) : (
          `❓ Generate Research Questions`
        )}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}

      {/* Research Questions Results */}
      <div className="flex-1 overflow-y-auto">
        {!questionsData ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-2xl mb-2">🤔</div>
            <div className="font-medium">Ready to Generate</div>
            <div className="text-xs mt-1">
              Click generate to discover research opportunities based on selected papers
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Processing Summary */}
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-600 space-y-1">
                <div>⏱️ Generated in {questionsData.processing_time_ms}ms</div>
                <div>📊 {questionsData.questions?.length || 0} questions generated</div>
              </div>
            </div>

            {/* Most Promising Direction */}
            {questionsData.most_promising_direction && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  🌟 Most Promising Direction
                </div>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="text-sm text-yellow-800 font-medium mb-2">
                    🎯 Recommended Focus
                  </div>
                  <div className="text-xs text-yellow-700">
                    {questionsData.most_promising_direction}
                  </div>
                </div>
              </div>
            )}

            {/* Generated Questions by Type */}
            {questionsData.questions && questionsData.questions.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  ❓ Research Questions
                </div>
                <div className="space-y-3">
                  {questionsData.questions.map((question, index) => {
                    const questionType = availableTypes.find(t => t.key === question.type);

                    return (
                      <div key={index} className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center space-x-2 mb-2">
                          <span className="text-sm">
                            {questionType?.icon || '❓'}
                          </span>
                          <span className="text-xs font-medium text-gray-700">
                            {questionType?.label || question.type}
                          </span>
                          {question.priority && (
                            <span className={`text-xs px-2 py-1 rounded ${
                              question.priority === 'high'
                                ? 'bg-red-100 text-red-700'
                                : question.priority === 'medium'
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-green-100 text-green-700'
                            }`}>
                              {question.priority}
                            </span>
                          )}
                        </div>

                        <div className="text-sm text-gray-900 font-medium mb-2">
                          {question.question}
                        </div>

                        {question.rationale && (
                          <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                            <div className="font-medium mb-1">💡 Rationale:</div>
                            {question.rationale}
                          </div>
                        )}

                        {question.potential_impact && (
                          <div className="text-xs text-blue-600 bg-blue-50 p-2 rounded mt-2">
                            <div className="font-medium mb-1">🎯 Potential Impact:</div>
                            {question.potential_impact}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Future Directions */}
            {questionsData.future_directions && questionsData.future_directions.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  🚀 Future Directions
                </div>
                <div className="space-y-2">
                  {questionsData.future_directions.map((direction, index) => (
                    <div key={index} className="bg-green-50 border border-green-200 rounded p-3">
                      <div className="text-xs text-green-800">
                        {direction}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Research Gaps */}
            {questionsData.research_gaps && questionsData.research_gaps.length > 0 && (
              <div>
                <div className="text-sm font-medium text-gray-900 mb-3">
                  🔍 Identified Research Gaps
                </div>
                <div className="space-y-2">
                  {questionsData.research_gaps.map((gap, index) => (
                    <div key={index} className="bg-red-50 border border-red-200 rounded p-3">
                      <div className="text-xs text-red-800">
                        {gap}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Export Actions */}
            <div className="pt-4 border-t border-gray-200">
              <div className="text-sm font-medium text-gray-900 mb-2">
                📤 Export Options
              </div>
              <div className="flex space-x-2">
                <button className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors">
                  📝 Export to Obsidian
                </button>
                <button className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors">
                  📋 Copy to Clipboard
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchQuestions;