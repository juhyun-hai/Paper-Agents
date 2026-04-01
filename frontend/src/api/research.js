import api from './client';

/**
 * Research Intelligence Platform API
 *
 * These functions call the new Research Intelligence endpoints
 * that provide AI-powered research analysis capabilities.
 */

/**
 * Analyze a research idea and get categorized paper recommendations
 */
export const analyzeResearchIdea = async ({ idea, goal = 'novelty' }) => {
  try {
    console.log('🔍 API Request:', { idea, goal });
    console.log('🌐 API Base URL:', import.meta.env.VITE_API_BASE_URL);

    const response = await api.post('/research/analyze', {
      idea,
      goal
    });

    console.log('✅ API Response received:', response);
    return response;
  } catch (error) {
    console.error('❌ Research analysis failed:', error);
    console.error('Error response:', error.response);
    console.error('Error data:', error.response?.data);
    console.error('Error status:', error.response?.status);

    const errorMessage = error.response?.data?.detail ||
                        error.response?.data?.message ||
                        error.message ||
                        'Failed to analyze research idea. Please try again.';

    throw new Error(errorMessage);
  }
};

/**
 * Compare selected papers with AI analysis
 */
export const comparePapers = async ({ paper_ids, focus_aspects = ['method', 'task', 'results'] }) => {
  try {
    if (!Array.isArray(paper_ids) || paper_ids.length < 2) {
      throw new Error('At least 2 papers required for comparison');
    }

    const response = await api.post('/research/compare', {
      paper_ids,
      focus_aspects
    });

    return response;
  } catch (error) {
    console.error('Paper comparison failed:', error);
    throw new Error(
      error.message || 'Failed to compare papers. Please try again.'
    );
  }
};

/**
 * Generate research questions based on selected papers
 */
export const generateResearchQuestions = async ({
  paper_ids,
  question_types = ['gap', 'extension', 'methodology']
}) => {
  try {
    if (!Array.isArray(paper_ids) || paper_ids.length === 0) {
      throw new Error('At least 1 paper required for question generation');
    }

    const response = await api.post('/research/questions', {
      paper_ids,
      question_types
    });

    return response;
  } catch (error) {
    console.error('Question generation failed:', error);
    throw new Error(
      error.message || 'Failed to generate research questions. Please try again.'
    );
  }
};

/**
 * Get platform status and health
 */
export const getPlatformStatus = async () => {
  try {
    const response = await api.get('/research/status');
    return response;
  } catch (error) {
    console.error('Status check failed:', error);
    throw new Error(
      error.message || 'Failed to check platform status.'
    );
  }
};

/**
 * Knowledge Graph API calls
 */
export const buildKnowledgeGraph = async (options = {}) => {
  try {
    const response = await api.post('/graph/build', {
      build_nodes: true,
      build_edges: true,
      edge_limit: 1000,
      ...options
    });

    return response;
  } catch (error) {
    console.error('Graph building failed:', error);
    throw new Error(
      error.message || 'Failed to build knowledge graph.'
    );
  }
};

export const getGraphStats = async () => {
  try {
    const response = await api.get('/graph/stats');
    return response;
  } catch (error) {
    console.error('Graph stats failed:', error);
    throw new Error(
      error.message || 'Failed to get graph statistics.'
    );
  }
};

export const getSubgraph = async ({ center_node_id, depth = 2, max_nodes = 50 }) => {
  try {
    const response = await api.post('/graph/subgraph', {
      center_node_id,
      depth,
      max_nodes
    });

    return response;
  } catch (error) {
    console.error('Subgraph query failed:', error);
    throw new Error(
      error.message || 'Failed to get subgraph.'
    );
  }
};

export const searchGraphNodes = async (query, nodeType = null, limit = 20) => {
  try {
    const params = { q: query, limit };
    if (nodeType) {
      params.node_type = nodeType;
    }

    const response = await api.get('/graph/nodes/search', { params });
    return response;
  } catch (error) {
    console.error('Graph node search failed:', error);
    throw new Error(
      error.message || 'Failed to search graph nodes.'
    );
  }
};

/**
 * Export research data to various formats
 */
export const exportToObsidian = async (data, format = 'full') => {
  // This would integrate with the Obsidian export system
  // For now, we'll implement client-side export

  try {
    // Format data for Obsidian markdown
    let markdown = '';

    if (data.analysis) {
      markdown += '# Research Analysis\n\n';
      markdown += `**Idea:** ${data.analysis.original_idea || 'N/A'}\n\n`;

      if (data.analysis.core_papers?.length > 0) {
        markdown += '## Core Papers\n\n';
        data.analysis.core_papers.forEach((paper, index) => {
          markdown += `${index + 1}. **${paper.title}**\n`;
          markdown += `   - Authors: ${paper.authors?.join(', ') || 'N/A'}\n`;
          markdown += `   - ArXiv: ${paper.arxiv_id || 'N/A'}\n`;
          if (paper.explanation) {
            markdown += `   - Why relevant: ${paper.explanation}\n`;
          }
          markdown += '\n';
        });
      }
    }

    if (data.comparison) {
      markdown += '\n## Paper Comparison\n\n';
      if (data.comparison.synthesis) {
        markdown += `**Overall Analysis:** ${data.comparison.synthesis}\n\n`;
      }
    }

    if (data.questions) {
      markdown += '\n## Research Questions\n\n';
      if (data.questions.questions?.length > 0) {
        data.questions.questions.forEach((q, index) => {
          markdown += `${index + 1}. **${q.question}**\n`;
          if (q.rationale) {
            markdown += `   - Rationale: ${q.rationale}\n`;
          }
          markdown += '\n';
        });
      }
    }

    // Create downloadable file
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research-session-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    return { success: true, format: 'markdown' };
  } catch (error) {
    console.error('Export failed:', error);
    throw new Error('Failed to export research data.');
  }
};