import React, { useState, useCallback } from 'react';
import ResearchInput from './research/ResearchInput';
import PaperRecommendations from './research/PaperRecommendations';
import PaperComparison from './research/PaperComparison';
import ResearchQuestions from './research/ResearchQuestions';

const ResearchDashboard = () => {
  const [analysisData, setAnalysisData] = useState(null);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [comparisonData, setComparisonData] = useState(null);
  const [questionsData, setQuestionsData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalysisComplete = useCallback((data) => {
    setAnalysisData(data);
  }, []);

  const handlePapersSelected = useCallback((papers) => {
    setSelectedPapers(papers);
  }, []);

  const handleComparisonComplete = useCallback((data) => {
    setComparisonData(data);
  }, []);

  const handleQuestionsComplete = useCallback((data) => {
    setQuestionsData(data);
  }, []);

  const clearAll = useCallback(() => {
    setAnalysisData(null);
    setSelectedPapers([]);
    setComparisonData(null);
    setQuestionsData(null);
  }, []);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Research Intelligence Platform
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              Transform research ideas into structured knowledge discovery
            </p>
          </div>
          <div className="flex space-x-3">
            {analysisData && (
              <button
                onClick={clearAll}
                className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Clear Session
              </button>
            )}
            <div className="text-sm text-gray-500 px-3 py-2 bg-green-50 rounded-lg border border-green-200">
              ✅ System Ready
            </div>
          </div>
        </div>
      </div>

      {/* 4-Panel Grid Layout */}
      <div className="flex-1 grid grid-cols-2 gap-1 p-1 bg-gray-100">

        {/* Top Left: Research Input & Analysis Trigger */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-4 py-3">
            <h2 className="text-lg font-semibold text-white flex items-center">
              <span className="text-xl mr-2">💡</span>
              Research Idea Analysis
            </h2>
            <p className="text-blue-100 text-sm mt-1">
              Transform your research idea into categorized paper recommendations
            </p>
          </div>
          <div className="p-4 h-full">
            <ResearchInput
              onAnalysisComplete={handleAnalysisComplete}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
            />
          </div>
        </div>

        {/* Top Right: Paper Recommendations */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-green-500 to-green-600 px-4 py-3">
            <h2 className="text-lg font-semibold text-white flex items-center">
              <span className="text-xl mr-2">📚</span>
              Paper Recommendations
            </h2>
            <p className="text-green-100 text-sm mt-1">
              Categorized papers with AI-powered explanations
            </p>
          </div>
          <div className="p-4 h-full overflow-y-auto">
            <PaperRecommendations
              analysisData={analysisData}
              onPapersSelected={handlePapersSelected}
              selectedPapers={selectedPapers}
            />
          </div>
        </div>

        {/* Bottom Left: Paper Comparison */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-purple-500 to-purple-600 px-4 py-3">
            <h2 className="text-lg font-semibold text-white flex items-center">
              <span className="text-xl mr-2">⚖️</span>
              Paper Comparison
            </h2>
            <p className="text-purple-100 text-sm mt-1">
              Side-by-side analysis with strengths and limitations
            </p>
          </div>
          <div className="p-4 h-full overflow-y-auto">
            <PaperComparison
              selectedPapers={selectedPapers}
              onComparisonComplete={handleComparisonComplete}
              comparisonData={comparisonData}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
            />
          </div>
        </div>

        {/* Bottom Right: Research Questions & Insights */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="bg-gradient-to-r from-orange-500 to-orange-600 px-4 py-3">
            <h2 className="text-lg font-semibold text-white flex items-center">
              <span className="text-xl mr-2">❓</span>
              Research Questions
            </h2>
            <p className="text-orange-100 text-sm mt-1">
              Identify research gaps and future opportunities
            </p>
          </div>
          <div className="p-4 h-full overflow-y-auto">
            <ResearchQuestions
              selectedPapers={selectedPapers}
              analysisData={analysisData}
              onQuestionsComplete={handleQuestionsComplete}
              questionsData={questionsData}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
            />
          </div>
        </div>

      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-20 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 flex items-center space-x-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <div>
              <div className="font-medium text-gray-900">Processing...</div>
              <div className="text-sm text-gray-600">This may take 10-30 seconds</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchDashboard;