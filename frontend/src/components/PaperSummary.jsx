import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { API_BASE } from '../api/client';

const PaperSummary = ({ arxivId, paper }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    console.log('🔍 PaperSummary mounted:', { arxivId, paper });

    if (!arxivId) {
      setError('No arXiv ID provided');
      setLoading(false);
      return;
    }

    loadSummary();
  }, [arxivId]);

  const loadSummary = async () => {
    setLoading(true);
    setError('');

    try {
      console.log(`📡 Loading summary for ${arxivId}...`);

      // Try to get summary from papers API first
      const paperResponse = await fetch(`${API_BASE}/papers/${arxivId}`);
      const paperData = await paperResponse.json();

      console.log('📋 Paper data:', paperData);

      if (paperData.summary && paperData.summary.summary_text) {
        console.log('✅ Found summary in paper data');
        setSummary(paperData.summary);
      } else {
        console.log('❌ No summary in paper data, trying summary API...');

        // Fallback to summary API
        const summaryResponse = await fetch(`${API_BASE}/summary/${arxivId}`);
        const summaryData = await summaryResponse.json();

        console.log('📋 Summary API data:', summaryData);

        if (summaryData.status === 'found') {
          setSummary(summaryData.summary);
        } else {
          setError('No summary available');
        }
      }
    } catch (err) {
      console.error('💥 Error loading summary:', err);
      setError(`Failed to load summary: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">요약 로딩 중...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-4">❌</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">오류 발생</h3>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={() => loadSummary()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">📄</div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          요약을 찾을 수 없습니다
        </h3>
        <p className="text-gray-600 mb-6">
          이 논문의 요약이 아직 생성되지 않았습니다.
        </p>
        <button
          onClick={() => loadSummary()}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
        >
          🔄 다시 확인
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Summary Header */}
      <div className="border-b border-gray-200 pb-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🤖</span>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Claude AI 요약</h2>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                {summary.generated_at && (
                  <span>생성일: {new Date(summary.generated_at).toLocaleDateString('ko-KR')}</span>
                )}
                {summary.word_count && (
                  <span>단어 수: {summary.word_count?.toLocaleString()}</span>
                )}
                <span className="px-2 py-1 rounded text-xs bg-green-100 text-green-800">
                  {summary.generation_model || 'Claude Sonnet 4'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Content */}
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown
          components={{
            h1: ({ children }) => <h1 className="text-2xl font-bold text-gray-900 mt-8 mb-4">{children}</h1>,
            h2: ({ children }) => <h2 className="text-xl font-semibold text-gray-900 mt-6 mb-3">{children}</h2>,
            h3: ({ children }) => <h3 className="text-lg font-medium text-gray-900 mt-4 mb-2">{children}</h3>,
            p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-4">{children}</p>,
            ul: ({ children }) => <ul className="list-disc pl-6 mb-4 text-gray-700">{children}</ul>,
            li: ({ children }) => <li className="mb-1">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
          }}
        >
          {summary.summary_text || '요약을 불러올 수 없습니다.'}
        </ReactMarkdown>
      </div>

    </div>
  );
};

export default PaperSummary;