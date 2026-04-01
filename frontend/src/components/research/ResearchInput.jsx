import React, { useState } from 'react';
import { analyzeResearchIdea } from '../../api/research';

const ResearchInput = ({ onAnalysisComplete, isLoading, setIsLoading }) => {
  const [researchIdea, setResearchIdea] = useState('');
  const [analysisGoal, setAnalysisGoal] = useState('novelty');
  const [error, setError] = useState('');

  const predefinedIdeas = [
    "using large language models for automated code generation and debugging",
    "multimodal transformers for visual question answering",
    "federated learning for privacy-preserving medical AI",
    "graph neural networks for drug discovery",
    "reinforcement learning for autonomous vehicle navigation"
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!researchIdea.trim()) return;

    setIsLoading(true);
    setError('');

    try {
      const result = await analyzeResearchIdea({
        idea: researchIdea.trim(),
        goal: analysisGoal
      });

      onAnalysisComplete(result);
    } catch (err) {
      setError(err.message || 'Failed to analyze research idea');
      console.error('Analysis error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePredefinedIdea = (idea) => {
    setResearchIdea(idea);
  };

  return (
    <div className="h-full flex flex-col">
      <form onSubmit={handleSubmit} className="flex-1 flex flex-col space-y-4">
        {/* Research Idea Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Research Idea
          </label>
          <textarea
            value={researchIdea}
            onChange={(e) => setResearchIdea(e.target.value)}
            placeholder="Describe your research idea, approach, or problem you want to explore..."
            className="w-full h-32 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
            disabled={isLoading}
          />
        </div>

        {/* Analysis Goal */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Analysis Goal
          </label>
          <select
            value={analysisGoal}
            onChange={(e) => setAnalysisGoal(e.target.value)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          >
            <option value="novelty">Find novelty gaps</option>
            <option value="survey">Literature survey</option>
            <option value="method">Method comparison</option>
            <option value="sota">State-of-the-art</option>
          </select>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!researchIdea.trim() || isLoading}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
              Analyzing...
            </div>
          ) : (
            '🔍 Analyze Research Idea'
          )}
        </button>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}
      </form>

      {/* Quick Start Examples */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Quick Start Examples:
        </h4>
        <div className="space-y-2 max-h-32 overflow-y-auto">
          {predefinedIdeas.map((idea, index) => (
            <button
              key={index}
              onClick={() => handlePredefinedIdea(idea)}
              className="w-full text-left text-xs text-gray-600 hover:text-blue-600 hover:bg-blue-50 px-2 py-2 rounded transition-colors"
              disabled={isLoading}
            >
              💡 {idea}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ResearchInput;