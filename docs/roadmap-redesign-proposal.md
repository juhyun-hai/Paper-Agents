# Roadmap Redesign: Schema and UI Changes

## Database Schema Changes

### 1. Alter `roadmap_papers` Table

```sql
-- New columns for enhanced paper ordering
ALTER TABLE roadmap_papers ADD COLUMN difficulty_level INTEGER DEFAULT 2;
ALTER TABLE roadmap_papers ADD COLUMN bloom_level TEXT DEFAULT 'analytical';
ALTER TABLE roadmap_papers ADD COLUMN importance_score REAL DEFAULT 3.0;
ALTER TABLE roadmap_papers ADD COLUMN importance_label TEXT DEFAULT 'recommended';
ALTER TABLE roadmap_papers ADD COLUMN depends_on TEXT DEFAULT '[]';
ALTER TABLE roadmap_papers ADD COLUMN concepts_introduced TEXT DEFAULT '[]';
ALTER TABLE roadmap_papers ADD COLUMN concepts_required TEXT DEFAULT '[]';
ALTER TABLE roadmap_papers ADD COLUMN what_to_focus_on TEXT DEFAULT '';
ALTER TABLE roadmap_papers ADD COLUMN reading_strategy TEXT DEFAULT '';
ALTER TABLE roadmap_papers ADD COLUMN section_name TEXT DEFAULT '';
ALTER TABLE roadmap_papers ADD COLUMN section_order INTEGER DEFAULT 0;
```

### 2. Alter `learning_roadmaps` Table

```sql
ALTER TABLE learning_roadmaps ADD COLUMN path_style TEXT DEFAULT 'bottom_up';
ALTER TABLE learning_roadmaps ADD COLUMN learning_objectives TEXT DEFAULT '[]';
ALTER TABLE learning_roadmaps ADD COLUMN target_audience TEXT DEFAULT '';
ALTER TABLE learning_roadmaps ADD COLUMN math_prerequisite TEXT DEFAULT 'none';
ALTER TABLE learning_roadmaps ADD COLUMN ml_prerequisite TEXT DEFAULT 'none';
```

---

## API Changes

### Enhanced GET /api/learning-roadmaps/{track_name} Response

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
    "Compare encoder-only vs decoder-only models"
  ],
  "math_prerequisite": "linear_algebra",
  "ml_prerequisite": "basic_deep_learning",
  "sections": [
    {
      "name": "Foundation",
      "order": 1,
      "description": "Core architecture papers",
      "papers": [
        {
          "arxiv_id": "1706.03762",
          "title": "Attention Is All You Need",
          "step_order": 1,
          "difficulty_level": 2,
          "bloom_level": "analytical",
          "importance_score": 4.45,
          "importance_label": "must_read",
          "depends_on": [],
          "concepts_introduced": ["self-attention", "multi-head attention"],
          "what_to_focus_on": "Section 3 (architecture). Skip Section 4.1 on first read.",
          "reading_strategy": "Read abstract and Section 3 first.",
          "why_important": "Foundation of all modern LLMs",
          "estimated_read_time": "1 week"
        }
      ]
    }
  ]
}
```

---

## Frontend UI Changes

### 1. Per-Paper Difficulty Badge

Replace the current plain step number with a difficulty-coded badge:

```
Level 1 (Conceptual) = Green circle
Level 2 (Analytical) = Blue circle
Level 3 (Technical) = Yellow circle
Level 4 (Integrative) = Orange circle
Level 5 (Frontier) = Red circle
```

### 2. Section Headers

Group papers under collapsible section headers:

```
[Section 1: Foundation] -------------------------
  "These papers introduce the core architecture."
  (1) Attention Is All You Need    [Must-Read] [Level 2]
  (2) BERT                         [Recommended] [Level 2]

[Section 2: Scale & Alignment] -------------------
  "How models grew and became useful."
  (3) GPT-3                        [Must-Read] [Level 3]
  (4) InstructGPT                  [Must-Read] [Level 3]
```

### 3. Importance Indicators

Color-coded labels next to each paper title:

- Must-Read: Gold/amber badge
- Recommended: Blue badge
- Supplementary: Gray badge (collapsible by default)
- Reference: Listed under "Further Reading" section

### 4. Path Style Toggle

At the top of each roadmap, a toggle button:

```
[Bottom-Up (Academic)] | [Top-Down (Practical)]
```

Switching reverses the display order and changes section labels.

### 5. Reading Strategy Tooltip

Each paper card shows a small info icon. On hover/click:

```
"Focus on: Section 3 (architecture) and the attention diagram.
 Skip: Detailed ablation studies in Section 6 on first read.
 Strategy: Read the abstract first, then jump to Section 3."
```

### 6. Prerequisite Arrows

When a paper has `depends_on` entries, show a small arrow/line connecting it to its prerequisite papers in the list. This visually communicates the dependency structure.

---

## Concrete Roadmap Data: LLM Beginner Track (Redesigned)

```python
REDESIGNED_LLM_BEGINNER = {
    "track_name": "llm_beginner",
    "track_title": "LLM Foundations",
    "description": "Build understanding of Large Language Models from the transformer architecture through modern instruction-tuned models.",
    "difficulty": "beginner",
    "estimated_time": "4-6 weeks",
    "path_style": "bottom_up",
    "target_audience": "ML practitioners or CS students new to LLMs",
    "learning_objectives": [
        "Understand the transformer architecture and self-attention mechanism",
        "Explain how pre-training and fine-tuning work",
        "Compare encoder-only (BERT) vs decoder-only (GPT) models",
        "Understand RLHF and instruction tuning",
        "Know the open-source LLM landscape"
    ],
    "math_prerequisite": "linear_algebra",
    "ml_prerequisite": "basic_deep_learning",
    "sections": [
        {
            "name": "The Transformer Revolution",
            "order": 1,
            "description": "The architecture that changed everything. Read these first.",
            "papers": [
                {
                    "arxiv_id": "1706.03762",
                    "step_order": 1,
                    "difficulty_level": 2,
                    "bloom_level": "analytical",
                    "importance_score": 4.45,
                    "importance_label": "must_read",
                    "depends_on": [],
                    "concepts_introduced": ["self-attention", "multi-head attention", "positional encoding", "encoder-decoder architecture"],
                    "concepts_required": ["sequence-to-sequence models", "neural network basics"],
                    "what_to_focus_on": "Section 3 (Model Architecture). The attention formula Q*K^T/sqrt(d_k) is the most important equation. Figure 1 shows the full architecture.",
                    "reading_strategy": "First pass: abstract + Section 3 + Figure 1. Second pass: Section 5 results. Skip Section 4.1 (regularization details) initially.",
                    "why_important": "Every modern LLM is built on this architecture. Understanding self-attention is the single most important concept.",
                    "estimated_read_time": "1 week"
                }
            ]
        },
        {
            "name": "Two Paths: Understanding vs Generation",
            "order": 2,
            "description": "The transformer spawned two paradigms: bidirectional encoding (BERT) and autoregressive generation (GPT).",
            "papers": [
                {
                    "arxiv_id": "1810.04805",
                    "step_order": 2,
                    "difficulty_level": 2,
                    "bloom_level": "analytical",
                    "importance_score": 3.85,
                    "importance_label": "recommended",
                    "depends_on": ["1706.03762"],
                    "concepts_introduced": ["masked language modeling", "bidirectional context", "fine-tuning paradigm", "pre-training + fine-tuning"],
                    "concepts_required": ["transformer encoder", "self-attention"],
                    "what_to_focus_on": "Section 3 (Pre-training tasks: MLM and NSP). Compare Figure 1 with the Transformer paper's encoder.",
                    "reading_strategy": "Focus on understanding WHY bidirectional context matters. The fine-tuning approach (Section 4) is the key innovation.",
                    "why_important": "BERT established the pre-train + fine-tune paradigm that all subsequent models follow.",
                    "estimated_read_time": "1 week"
                },
                {
                    "arxiv_id": "2005.14165",
                    "step_order": 3,
                    "difficulty_level": 3,
                    "bloom_level": "integrative",
                    "importance_score": 4.45,
                    "importance_label": "must_read",
                    "depends_on": ["1706.03762"],
                    "concepts_introduced": ["scaling laws", "few-shot learning", "in-context learning", "emergent abilities"],
                    "concepts_required": ["transformer decoder", "autoregressive generation"],
                    "what_to_focus_on": "Section 1 (Introduction with scaling argument), Section 3 (Results showing few-shot performance). Table 3.1 is key.",
                    "reading_strategy": "This is a long paper (75 pages). Read Sections 1-3 first. Section 4+ is detailed benchmarks -- skim for patterns, don't memorize numbers.",
                    "why_important": "Demonstrated that scale alone unlocks new capabilities. The paper that launched the modern LLM era.",
                    "estimated_read_time": "1-2 weeks"
                }
            ]
        },
        {
            "name": "Making Models Useful",
            "order": 3,
            "description": "Raw language models are powerful but hard to control. These papers show how to align them with human intent.",
            "papers": [
                {
                    "arxiv_id": "2203.02155",
                    "step_order": 4,
                    "difficulty_level": 3,
                    "bloom_level": "technical",
                    "importance_score": 4.05,
                    "importance_label": "must_read",
                    "depends_on": ["2005.14165"],
                    "concepts_introduced": ["RLHF", "reward modeling", "instruction tuning", "human preference alignment"],
                    "concepts_required": ["language model pre-training", "fine-tuning"],
                    "what_to_focus_on": "Section 3 (Methods: SFT + RM + PPO pipeline). Figure 2 is the key diagram. Section 6 (limitations) is surprisingly important.",
                    "reading_strategy": "Understand the 3-step pipeline (SFT > Reward Model > PPO). Don't get lost in the RL math -- focus on the intuition.",
                    "why_important": "This is how ChatGPT works. The RLHF pipeline became the standard for making LLMs follow instructions safely.",
                    "estimated_read_time": "1 week"
                }
            ]
        },
        {
            "name": "The Open-Source Response",
            "order": 4,
            "description": "Open-weight models democratized access to LLM capabilities.",
            "papers": [
                {
                    "arxiv_id": "2302.13971",
                    "step_order": 5,
                    "difficulty_level": 2,
                    "bloom_level": "analytical",
                    "importance_score": 3.65,
                    "importance_label": "recommended",
                    "depends_on": ["2203.02155"],
                    "concepts_introduced": ["efficient pre-training", "open-weight models", "data quality over model size"],
                    "concepts_required": ["transformer architecture", "scaling laws", "instruction tuning"],
                    "what_to_focus_on": "Section 2 (Approach: data mixture and training details). Table 1 (model sizes). The key insight is that data quality matters more than model size.",
                    "reading_strategy": "Shorter and more practical than GPT-3. Read end-to-end. Compare training choices with GPT-3.",
                    "why_important": "LLaMA proved that smaller, well-trained models can match larger ones, launching the open-source LLM movement.",
                    "estimated_read_time": "1 week"
                }
            ]
        }
    ]
}
```

---

## Migration Script Outline

```python
def migrate_roadmap_schema():
    """Add new columns to support enhanced paper ordering."""
    
    # 1. ALTER TABLE roadmap_papers
    new_paper_columns = [
        ("difficulty_level", "INTEGER DEFAULT 2"),
        ("bloom_level", "TEXT DEFAULT 'analytical'"),
        ("importance_score", "REAL DEFAULT 3.0"),
        ("importance_label", "TEXT DEFAULT 'recommended'"),
        ("depends_on", "TEXT DEFAULT '[]'"),
        ("concepts_introduced", "TEXT DEFAULT '[]'"),
        ("concepts_required", "TEXT DEFAULT '[]'"),
        ("what_to_focus_on", "TEXT DEFAULT ''"),
        ("reading_strategy", "TEXT DEFAULT ''"),
        ("section_name", "TEXT DEFAULT ''"),
        ("section_order", "INTEGER DEFAULT 0"),
    ]
    
    # 2. ALTER TABLE learning_roadmaps
    new_roadmap_columns = [
        ("path_style", "TEXT DEFAULT 'bottom_up'"),
        ("learning_objectives", "TEXT DEFAULT '[]'"),
        ("target_audience", "TEXT DEFAULT ''"),
        ("math_prerequisite", "TEXT DEFAULT 'none'"),
        ("ml_prerequisite", "TEXT DEFAULT 'none'"),
    ]
    
    # 3. Backfill existing data with sensible defaults
    # 4. Update API endpoints to return new fields
    # 5. Update frontend components to render new data
```

---

## Summary of Changes

| Area | Current State | Proposed State |
|---|---|---|
| Difficulty | Roadmap-level only (beginner/intermediate/advanced) | Per-paper 5-level + Bloom's taxonomy level |
| Prerequisites | None (flat ordered list) | Per-paper DAG with typed prerequisite edges |
| Importance | Cosmetic labels (essential/advanced/cutting_edge) | Scored 1.0-5.0 with evidence-based labels |
| Paper grouping | Flat numbered list | Sections with narrative descriptions |
| Reading guidance | "why_important" text only | Why + What to focus on + Reading strategy |
| Path options | Single ordering | Bottom-up and Top-down toggleable paths |
| Concept tracking | None | concepts_introduced / concepts_required per paper |
| Validation | Scripts clean up bad data | API-level validation against papers table |
