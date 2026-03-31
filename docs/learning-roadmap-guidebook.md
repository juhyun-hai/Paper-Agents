# Learning Roadmap Paper Ordering Guidebook

## Evidence-Based Design for the Paper Agent Learning Page

**Version:** 1.0
**Date:** 2026-03-31
**Based on:** Research from Papers With Code, DeepLearning.AI, fast.ai, MIT OCW, cognitive load theory, and educational knowledge graph literature.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Findings by Platform](#2-research-findings-by-platform)
3. [Core Ordering Principles](#3-core-ordering-principles)
4. [Paper Difficulty Classification System](#4-paper-difficulty-classification-system)
5. [Prerequisite Mapping Model](#5-prerequisite-mapping-model)
6. [Importance Scoring Framework](#6-importance-scoring-framework)
7. [Recommended Roadmap Structure](#7-recommended-roadmap-structure)
8. [Current System Gaps and Fixes](#8-current-system-gaps-and-fixes)
9. [Implementation Recommendations](#9-implementation-recommendations)

---

## 1. Executive Summary

The current Paper Agent learning roadmap system has a solid foundation but lacks several evidence-based features that top educational platforms use to optimize learning outcomes. Key gaps:

- **No multi-dimensional difficulty classification** -- papers are tagged only at the roadmap level (beginner/intermediate/advanced), not per-paper.
- **No prerequisite graph** -- papers are listed in a flat ordered list without explicit dependency edges.
- **No learner-level adaptation** -- the same ordering is shown to all users regardless of background.
- **Priority labels are cosmetic** -- "essential/advanced/cutting_edge" are marketing labels, not pedagogical difficulty indicators.
- **No concept-based scaffolding** -- papers jump between unrelated concepts without building on each other.

This guidebook provides a concrete framework to fix these issues.

---

## 2. Research Findings by Platform

### 2.1 Papers With Code
- **Organization model:** Taxonomy-based (task > method > dataset > benchmark)
- **Ordering:** By trending score (stars/popularity), not pedagogical sequence
- **Strength:** Excellent for discovery; weak for structured learning
- **Key lesson:** Popularity-based ordering is not suitable for learning paths. Our system must differentiate between "trending" and "educational."

### 2.2 DeepLearning.AI
- **Organization model:** Specializations (multi-course) + Short Courses (modular)
- **Difficulty tiers:** Beginner (59 courses), Intermediate (62 courses), Advanced
- **Ordering within specialization:** Prescribed sequential order, with explicit prerequisites
- **Pedagogy:** Intuition-first > Math > Code & Labs (three-phase cycle per topic)
- **Key lesson:** Each learning unit should follow a consistent internal structure: motivation > concept > application. Papers in a roadmap should be ordered so each paper's "method" section is understandable given the prior papers.

### 2.3 fast.ai
- **Organization model:** Top-down, example-first pedagogy
- **Ordering:** Start with working end-to-end examples, progressively reveal internals
- **Progression:** Practical application > Model mechanics > Mathematical foundations
- **Key lesson:** Foundational papers (like "Attention Is All You Need") should NOT necessarily come first for all learners. A top-down track could start with a practical application paper (e.g., a fine-tuning paper) and link back to the transformer paper as a reference.

### 2.4 MIT OpenCourseWare
- **Organization model:** Strict prerequisite chains (e.g., 6.0001 > 6.0002, 18.01 > 6.042)
- **Ordering:** Bottom-up, mathematical rigor first
- **Key lesson:** For academic/research-oriented tracks, prerequisite chains should be explicit and enforced. Each paper should list which prior papers the reader should have read.

### 2.5 Educational Knowledge Graphs (Research Literature)
- **Organization model:** DAG (Directed Acyclic Graph) of concepts with prerequisite edges
- **Ordering:** Topological sort of concept dependencies
- **Key lesson:** The optimal data structure for paper ordering is a prerequisite DAG, not a flat list. The existing `paper_relationships` table partially supports this but is underutilized in the UI.

---

## 3. Core Ordering Principles

Based on the research, paper ordering should follow these six principles:

### Principle 1: Prerequisite-Respecting Order
Every paper in a roadmap must come after all papers it conceptually depends on. This is the minimum correctness constraint.

**Example:** "BERT" (1810.04805) must come after "Attention Is All You Need" (1706.03762) because BERT's architecture is the transformer encoder.

### Principle 2: Cognitive Load Progression (Simple-to-Complex)
Within each prerequisite-valid ordering, prefer the sequence that introduces fewer new concepts per step. From cognitive load theory:
- **Intrinsic load** (paper complexity) should increase gradually
- **Extraneous load** (unfamiliar notation, unexplained terms) should be minimized by prior papers
- **Germane load** (effort to connect new ideas to prior knowledge) should be supported by explicit "why this matters" context

**Metric:** Each paper should introduce at most 2-3 new major concepts beyond what prior papers covered.

### Principle 3: Motivate Before Formalize
Following fast.ai's top-down principle and DeepLearning.AI's "intuition first" approach:
- Before a highly mathematical paper, include a paper that demonstrates the practical impact
- Before a foundational architecture paper, show what it enables

**Example in CV track:**
1. Show CLIP results (practical impact) > 2. ViT architecture (how it works) > 3. Self-supervised learning theory (why it works)

### Principle 4: Interleave Related Concepts
From learning science research on interleaving:
- Don't cluster all "transformer papers" together, then all "efficiency papers"
- Instead, alternate: architecture > application > efficiency > next architecture
- This forces the learner to compare and discriminate, improving retention

### Principle 5: Explicit Difficulty Markers Per Paper
Every paper should have its own difficulty rating independent of the roadmap difficulty. A "beginner" roadmap may still include an "intermediate" paper if it is essential and properly scaffolded.

### Principle 6: Multiple Valid Paths
There is no single correct ordering. Provide at least two path styles:
- **Bottom-up (academic):** Foundations first, then applications (MIT OCW style)
- **Top-down (practical):** Applications first, then deep-dive into foundations (fast.ai style)

---

## 4. Paper Difficulty Classification System

### 4.1 Bloom's Taxonomy Mapping for Papers

Each paper should be classified on a 5-level scale based on what the reader must DO to understand it:

| Level | Label | Description | Example Papers |
|-------|-------|-------------|----------------|
| 1 | **Conceptual** | Reader needs to understand the high-level idea. Mostly intuitive. | Survey papers, "Attention Is All You Need" (concept level) |
| 2 | **Analytical** | Reader needs to follow mathematical derivations or architectural details. | BERT, ResNet |
| 3 | **Technical** | Reader needs to understand implementation details, training procedures, loss functions. | LoRA, QLoRA, DDPM |
| 4 | **Integrative** | Reader must synthesize knowledge from multiple prior papers to understand the contribution. | RAG, Stable Diffusion, CLIP |
| 5 | **Frontier** | Cutting-edge; assumes deep familiarity with the entire subfield. | Latest arxiv papers, novel architectures |

### 4.2 Required Background Dimensions

Each paper should also be tagged with required background along three axes:

- **Math level:** None / Linear Algebra / Probability / Optimization / Advanced
- **ML level:** None / Basic ML / Deep Learning / Specific Architecture Knowledge
- **Domain level:** None / NLP Basics / CV Basics / RL Basics / Multi-domain

### 4.3 Difficulty Score Formula

```
difficulty_score = (
    bloom_level * 0.4 +
    math_requirement * 0.3 +
    prerequisite_count * 0.2 +
    paper_length_factor * 0.1
)
```

Where:
- `bloom_level`: 1-5 as above
- `math_requirement`: 1-5 (none to advanced)
- `prerequisite_count`: number of papers that should be read first (normalized 0-5)
- `paper_length_factor`: 1 (short, <10 pages), 2 (medium), 3 (long, >30 pages)

---

## 5. Prerequisite Mapping Model

### 5.1 Prerequisite Edge Types

The existing `paper_relationships` table uses types: `cites`, `builds_on`, `improves`, `applies`, `motivates`, `influences`, `complements`. For learning path ordering, we should add a learning-specific classification:

| Prerequisite Type | Learning Meaning | Ordering Constraint |
|---|---|---|
| **hard_prerequisite** | Cannot understand B without reading A first | A must precede B, no exceptions |
| **soft_prerequisite** | Understanding B is easier with A, but B is readable alone | A should precede B, but can be skipped by experienced readers |
| **recommended_context** | A provides useful background for B but is not necessary | A is linked from B but not required in the same roadmap |
| **parallel** | A and B cover different aspects of the same concept; order doesn't matter | Either can come first |

### 5.2 Prerequisite Graph Construction Rules

1. For each paper in a roadmap, list the key concepts it introduces and the key concepts it assumes
2. If paper B assumes concept C, and paper A is the first paper in the roadmap that introduces C, then A -> B is a `hard_prerequisite`
3. If paper B references concept C but can be understood without deep C knowledge, and paper A introduces C, then A -> B is a `soft_prerequisite`
4. Run topological sort on the prerequisite graph to determine valid orderings
5. Among valid orderings, choose the one that minimizes cognitive load jumps (Principle 2)

### 5.3 Example: LLM Beginner Track Prerequisite Graph

```
Attention Is All You Need (1706.03762)
    |--[hard]---> BERT (1810.04805)
    |--[hard]---> GPT-3 (2005.14165)
                    |--[hard]---> InstructGPT (2203.02155)
                                    |--[soft]---> LLaMA (2302.13971)
```

Valid orderings:
1. Transformer > BERT > GPT-3 > InstructGPT > LLaMA (current)
2. Transformer > GPT-3 > BERT > InstructGPT > LLaMA (also valid)

Option 1 is better because BERT is simpler than GPT-3 (fewer concepts, smaller scale), following Principle 2.

---

## 6. Importance Scoring Framework

### 6.1 Why Importance Scoring Matters

Not all papers in a roadmap are equally essential. The current system uses `priority` (essential/advanced/cutting_edge) but this conflates time-relevance with pedagogical importance. We need a multi-dimensional importance score.

### 6.2 Importance Dimensions

| Dimension | Weight | Description |
|---|---|---|
| **Foundational Impact** | 0.30 | How many subsequent papers depend on this one? |
| **Concept Density** | 0.25 | How many unique, reusable concepts does this paper introduce? |
| **Citation Influence** | 0.15 | Citation count as a proxy for community validation |
| **Practical Applicability** | 0.20 | Can the reader apply the paper's ideas in their own work? |
| **Recency Relevance** | 0.10 | Is this still the state-of-the-art or has it been superseded? |

### 6.3 Importance Score Calculation

```
importance_score = (
    foundational_impact * 0.30 +
    concept_density * 0.25 +
    citation_influence * 0.15 +
    practical_applicability * 0.20 +
    recency_relevance * 0.10
)
```

Each dimension is rated 1-5. Final score range: 1.0 - 5.0.

### 6.4 Importance Labels

| Score Range | Label | UI Treatment |
|---|---|---|
| 4.0 - 5.0 | **Must-Read** | Highlighted, cannot be skipped |
| 3.0 - 3.9 | **Recommended** | Standard display, encouraged |
| 2.0 - 2.9 | **Supplementary** | Collapsible, for deeper exploration |
| 1.0 - 1.9 | **Reference** | Listed as "further reading" only |

### 6.5 Example Scoring: LLM Beginner Track

| Paper | Foundational | Concept Density | Citations | Practical | Recency | Total | Label |
|---|---|---|---|---|---|---|---|
| Attention Is All You Need | 5 | 5 | 5 | 4 | 3 | **4.45** | Must-Read |
| BERT | 4 | 4 | 5 | 4 | 2 | **3.85** | Recommended |
| GPT-3 | 5 | 4 | 5 | 5 | 3 | **4.45** | Must-Read |
| InstructGPT | 4 | 4 | 4 | 5 | 3 | **4.05** | Must-Read |
| LLaMA | 3 | 3 | 4 | 5 | 4 | **3.65** | Recommended |

---

## 7. Recommended Roadmap Structure

### 7.1 Roadmap Metadata (Enhanced)

Each roadmap should include:

```json
{
  "track_name": "llm_beginner",
  "track_title": "LLM Foundations",
  "description": "...",
  "difficulty": "beginner",
  "estimated_time": "4-6 weeks",
  "path_style": "bottom_up",
  "target_audience": "ML practitioners new to LLMs",
  "learning_objectives": [
    "Understand the transformer architecture",
    "Explain how pre-training and fine-tuning work",
    "Compare encoder-only vs decoder-only models",
    "Understand RLHF and instruction tuning"
  ],
  "prerequisites": {
    "math": "linear_algebra",
    "ml": "basic_deep_learning",
    "domain": "none"
  }
}
```

### 7.2 Paper Entry (Enhanced)

Each paper in a roadmap should include:

```json
{
  "arxiv_id": "1706.03762",
  "step_order": 1,
  "difficulty_level": 2,
  "bloom_level": "analytical",
  "importance_score": 4.45,
  "importance_label": "must_read",
  "prerequisite_type": null,
  "depends_on": [],
  "concepts_introduced": ["self-attention", "multi-head attention", "positional encoding", "encoder-decoder"],
  "concepts_required": ["sequence-to-sequence", "neural networks"],
  "why_important": "Introduces the transformer architecture that underlies all modern LLMs and vision models",
  "what_to_focus_on": "Section 3 (architecture) and Section 5 (results). Skip Section 4.1 on first read.",
  "estimated_read_time": "1 week",
  "reading_strategy": "Read abstract and Section 3 first. Return to math details after seeing BERT/GPT applications."
}
```

### 7.3 Section Grouping Within Roadmaps

Papers within a roadmap should be grouped into sections that form a narrative:

```
Section 1: Foundation (papers 1-2)
  "These papers introduce the core architecture you'll use throughout."

Section 2: Understanding (papers 3-4)
  "These papers show how the foundation is applied to language tasks."

Section 3: Alignment (paper 5)
  "This paper shows how models are made safe and useful."

Section 4: Open Models (paper 6)
  "The open-source response and efficiency improvements."

Section 5: Latest Developments (papers 7+)
  "Where the field is headed now."
```

### 7.4 Dual-Path Option

For each major topic, offer two entry paths:

**Bottom-Up Path (Academic):**
Transformer > BERT > GPT-3 > InstructGPT > LLaMA

**Top-Down Path (Practical):**
LLaMA (run it) > InstructGPT (how it's trained) > GPT-3 (why scale matters) > BERT (encoder variant) > Transformer (the foundation)

The user selects their preferred path style in the UI.

---

## 8. Current System Gaps and Fixes

### Gap 1: Flat Paper List Without Prerequisite Edges
**Current:** `roadmap_papers` table has `step_order` (integer) only.
**Fix:** Add `depends_on` field (JSON array of arxiv_ids) and `prerequisite_type` field to `roadmap_papers`.

### Gap 2: No Per-Paper Difficulty
**Current:** Difficulty is only on the roadmap level.
**Fix:** Add `difficulty_level` (1-5 integer) and `bloom_level` (text enum) to `roadmap_papers`.

### Gap 3: No Concept Tracking
**Current:** No tracking of what concepts each paper introduces or requires.
**Fix:** Add `concepts_introduced` and `concepts_required` (JSON arrays) to `roadmap_papers`.

### Gap 4: Cosmetic Priority Labels
**Current:** `priority` field uses "essential/advanced/cutting_edge" -- these are time-based, not importance-based.
**Fix:** Replace with `importance_score` (float 1.0-5.0) and `importance_label` (must_read/recommended/supplementary/reference).

### Gap 5: No Reading Guidance
**Current:** Only `why_important` is provided.
**Fix:** Add `what_to_focus_on` (which sections to prioritize) and `reading_strategy` (how to approach the paper).

### Gap 6: No Section Grouping
**Current:** Papers are a flat numbered list.
**Fix:** Add `section_name` and `section_description` fields to group papers into narrative sections.

### Gap 7: No Path Style Support
**Current:** Single ordering per roadmap.
**Fix:** Allow multiple orderings per roadmap with a `path_style` tag (bottom_up, top_down).

### Gap 8: Invalid Papers in Roadmaps
**Current:** Some roadmaps reference arxiv IDs that don't exist in the DB or are irrelevant (math papers in CV tracks).
**Fix:** Validate all arxiv_ids against the papers table before display. The `restructure_roadmaps.py` script already tries to clean these, but validation should happen at the API level.

---

## 9. Implementation Recommendations

### Phase 1: Data Model Improvements (Priority: High)

1. **Add columns to `roadmap_papers` table:**
   - `difficulty_level` INTEGER DEFAULT 2
   - `bloom_level` TEXT DEFAULT 'analytical'
   - `importance_score` REAL DEFAULT 3.0
   - `importance_label` TEXT DEFAULT 'recommended'
   - `depends_on` TEXT DEFAULT '[]' (JSON array)
   - `concepts_introduced` TEXT DEFAULT '[]' (JSON array)
   - `concepts_required` TEXT DEFAULT '[]' (JSON array)
   - `what_to_focus_on` TEXT DEFAULT ''
   - `reading_strategy` TEXT DEFAULT ''
   - `section_name` TEXT DEFAULT ''
   - `section_order` INTEGER DEFAULT 0

2. **Add `path_style` and `learning_objectives` to `learning_roadmaps` table:**
   - `path_style` TEXT DEFAULT 'bottom_up'
   - `learning_objectives` TEXT DEFAULT '[]' (JSON array)
   - `target_audience` TEXT DEFAULT ''
   - `math_prerequisite` TEXT DEFAULT 'none'
   - `ml_prerequisite` TEXT DEFAULT 'none'

### Phase 2: UI Improvements (Priority: High)

1. **Per-paper difficulty badges** in the roadmap expansion view
2. **Section headers** grouping related papers with narrative descriptions
3. **Prerequisite visualization** showing dependency arrows between papers
4. **Importance indicators** (color-coded: must-read = gold, recommended = blue, supplementary = gray)
5. **Reading strategy tooltips** on each paper card
6. **Path style toggle** (Bottom-up / Top-down) at the top of each roadmap

### Phase 3: Content Quality (Priority: Medium)

1. **Audit all existing roadmaps** against the prerequisite graph rules
2. **Remove invalid paper references** (papers not in DB)
3. **Add reading guidance** (what_to_focus_on, reading_strategy) for all papers
4. **Score all papers** using the importance scoring framework
5. **Classify all papers** using the difficulty classification system

### Phase 4: Advanced Features (Priority: Low)

1. **Progress tracking** -- let users mark papers as read and track completion
2. **Adaptive ordering** -- reorder based on user's stated background
3. **Concept mastery map** -- show which concepts the user has covered
4. **Auto-suggest next paper** based on the prerequisite graph and user progress

---

## Appendix A: Platform Comparison Matrix

| Feature | Papers With Code | DeepLearning.AI | fast.ai | MIT OCW | Paper Agent (Current) | Paper Agent (Proposed) |
|---|---|---|---|---|---|---|
| Difficulty levels | None | 3-tier | 2-part | Implicit | Roadmap-level only | Per-paper 5-level |
| Prerequisites | None | Per-course | Minimal | Strict chains | None | Per-paper DAG |
| Ordering model | Popularity | Sequential | Top-down | Bottom-up | Flat list | Prerequisite-sorted |
| Learning objectives | None | Per-course | Per-lesson | Per-course | None | Per-roadmap |
| Reading guidance | None | Video + quiz | Video + code | Lecture + problem sets | "why_important" only | Full strategy |
| Multiple paths | None | Specialization choice | 2 parts | Electives | None | Bottom-up / Top-down |
| Progress tracking | None | Completion % | Completion % | None | None | Proposed Phase 4 |

---

## Appendix B: Key References

- Sweller, J. (1988). "Cognitive Load During Problem Solving: Effects on Learning." Cognitive Science.
- Anderson, L.W. & Krathwohl, D.R. (2001). "A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy."
- Roediger, H.L. & Karpicke, J.D. (2006). "The Power of Testing Memory: Basic Research and Implications for Educational Practice."
- Kang, S.H.K. (2016). "Spaced Repetition Promotes Efficient and Effective Learning."
- Educational Knowledge Graphs with Prerequisite Relations (JEDM, 2025).
