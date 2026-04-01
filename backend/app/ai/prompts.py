"""
Prompt templates for research intelligence analysis.
"""

from typing import List, Dict, Any


class ResearchPrompts:
    """Research analysis prompt templates."""

    @staticmethod
    def explain_paper_relevance(
        user_idea: str,
        paper_title: str,
        paper_abstract: str,
        similarity_score: float
    ) -> List[Dict[str, str]]:
        """Generate explanation for why a paper is relevant."""
        return [
            {
                "role": "system",
                "content": """You are a research intelligence assistant. Analyze why a paper is relevant to a user's research idea.

                Provide clear, specific explanations focusing on:
                - Task/problem similarity
                - Method/approach connections
                - Potential gaps or extensions
                - Practical applications

                Be concise but insightful. Avoid generic statements."""
            },
            {
                "role": "user",
                "content": f"""
                User's Research Idea:
                {user_idea}

                Paper Title: {paper_title}
                Abstract: {paper_abstract}
                Similarity Score: {similarity_score:.3f}

                Explain specifically why this paper is relevant to the user's idea. What connections do you see?
                """
            }
        ]

    @staticmethod
    def analyze_research_direction(
        user_idea: str,
        goal: str,
        papers_context: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Generate comprehensive research direction analysis."""

        papers_summary = "\n\n".join([
            f"Title: {p['title']}\nAbstract: {p['abstract'][:200]}..."
            for p in papers_context[:10]  # Limit context size
        ])

        return [
            {
                "role": "system",
                "content": f"""You are a research strategy advisor. Analyze a research landscape and provide strategic insights.

                The user's goal is: {goal}

                Your analysis should include:
                - Key insights from the paper landscape
                - Identified research gaps
                - Recommended research directions
                - Potential challenges and opportunities

                Be specific and actionable. Focus on novelty and impact."""
            },
            {
                "role": "user",
                "content": f"""
                Research Idea: {user_idea}
                Goal: {goal}

                Related Papers Context:
                {papers_summary}

                Provide a strategic analysis of this research direction. What are the key insights, gaps, and recommendations?
                """
            }
        ]

    @staticmethod
    def compare_papers(
        papers: List[Dict[str, Any]],
        focus_aspects: List[str]
    ) -> List[Dict[str, str]]:
        """Generate paper comparison analysis."""

        papers_info = []
        for i, paper in enumerate(papers, 1):
            papers_info.append(f"""
            Paper {i}: {paper['title']}
            Authors: {', '.join(paper.get('authors', []))}
            Abstract: {paper.get('abstract', '')[:300]}...
            """)

        papers_text = "\n".join(papers_info)

        return [
            {
                "role": "system",
                "content": f"""You are a research analyst specializing in comparative analysis. Compare research papers across multiple dimensions.

                Focus aspects for comparison: {', '.join(focus_aspects)}

                For each paper, analyze:
                - Strengths and limitations
                - Novel contributions
                - Methodological approaches
                - Results and evaluation

                Then provide cross-paper analysis:
                - Common themes and differences
                - Complementary vs conflicting findings
                - Best paper for different use cases

                Be precise and evidence-based."""
            },
            {
                "role": "user",
                "content": f"""
                Papers to Compare:
                {papers_text}

                Provide a comprehensive comparison focusing on: {', '.join(focus_aspects)}

                Include both individual paper analysis and cross-paper insights.
                """
            }
        ]

    @staticmethod
    def generate_research_questions(
        papers: List[Dict[str, Any]],
        focus_area: str = None,
        question_types: List[str] = None
    ) -> List[Dict[str, str]]:
        """Generate research questions from paper analysis."""

        question_types = question_types or ["gap", "extension", "methodology"]

        papers_summary = "\n\n".join([
            f"Title: {p['title']}\nKey findings: {p.get('abstract', '')[:150]}..."
            for p in papers[:8]  # Limit context
        ])

        focus_instruction = f"Focus area: {focus_area}" if focus_area else ""

        return [
            {
                "role": "system",
                "content": f"""You are a research question generator. Identify novel research directions from existing papers.

                Question types to generate: {', '.join(question_types)}
                {focus_instruction}

                For each question:
                - Ensure it addresses a genuine gap or opportunity
                - Make it specific and actionable
                - Assess feasibility and potential impact
                - Provide supporting evidence

                Question types:
                - gap: unexplored areas or missing links
                - contradiction: conflicting findings to resolve
                - extension: ways to build upon existing work
                - application: novel applications of methods
                - methodology: improvements to approaches

                Generate 3-5 high-quality questions."""
            },
            {
                "role": "user",
                "content": f"""
                Papers to analyze:
                {papers_summary}

                Generate research questions that address gaps, extensions, and methodological improvements in this area.
                """
            }
        ]

    @staticmethod
    def categorize_papers(
        user_idea: str,
        papers: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Categorize papers into different relevance types."""

        papers_list = "\n".join([
            f"{i+1}. {p['title']} (Score: {p.get('similarity_score', 0):.3f})"
            for i, p in enumerate(papers[:20])
        ])

        return [
            {
                "role": "system",
                "content": """You are a research categorization expert. Categorize papers based on their relationship to a user's research idea.

                Categories:
                - core_papers: Directly address the same problem/task
                - method_neighbors: Use similar methods but different tasks
                - task_neighbors: Address similar tasks with different methods
                - recent_trends: Recent developments in the area
                - gap_candidates: Papers that reveal gaps or limitations
                - contrasting_papers: Take different approaches or contradict assumptions

                For each paper, determine its primary category based on the relationship to the user's idea."""
            },
            {
                "role": "user",
                "content": f"""
                User Research Idea: {user_idea}

                Papers to categorize:
                {papers_list}

                Categorize each paper by its relationship to the user's research idea. Return the paper number and category for each.
                """
            }
        ]


class ComparisonSchema:
    """JSON schema for paper comparison response."""

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["comparison", "common_themes", "key_differences", "comparison_matrix"],
            "properties": {
                "comparison": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["title", "strengths", "limitations", "relevance_to_user", "priority"],
                        "properties": {
                            "title": {"type": "string"},
                            "task": {"type": "string"},
                            "method": {"type": "string"},
                            "dataset": {"type": "string"},
                            "key_results": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "limitations": {"type": "array", "items": {"type": "string"}},
                            "novelty_aspects": {"type": "array", "items": {"type": "string"}},
                            "relevance_to_user": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                        }
                    }
                },
                "common_themes": {"type": "array", "items": {"type": "string"}},
                "key_differences": {"type": "array", "items": {"type": "string"}},
                "complementary_aspects": {"type": "array", "items": {"type": "string"}},
                "conflicting_findings": {"type": "array", "items": {"type": "string"}},
                "best_for_implementation": {"type": "string"},
                "best_for_theoretical_foundation": {"type": "string"},
                "most_recent_approach": {"type": "string"},
                "comparison_matrix": {"type": "object"}
            }
        }


class QuestionsSchema:
    """JSON schema for research questions response."""

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["questions", "most_promising_direction", "research_landscape_summary"],
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["question", "type", "confidence", "novelty_score", "difficulty", "evidence"],
                        "properties": {
                            "question": {"type": "string"},
                            "type": {"type": "string", "enum": ["gap", "contradiction", "extension", "application", "methodology"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "novelty_score": {"type": "number", "minimum": 0, "maximum": 1},
                            "difficulty": {"type": "string", "enum": ["low", "medium", "high"]},
                            "evidence": {"type": "string"},
                            "related_papers": {"type": "array", "items": {"type": "string"}},
                            "suggested_approaches": {"type": "array", "items": {"type": "string"}},
                            "potential_impact": {"type": "string"}
                        }
                    }
                },
                "most_promising_direction": {"type": "string"},
                "research_landscape_summary": {"type": "string"},
                "knowledge_gaps_identified": {"type": "array", "items": {"type": "string"}}
            }
        }