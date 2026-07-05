-- 005: 오늘의 연구 흐름 요약 (daily overview briefing)
-- 매일 featured 25편 기반 3-4문장 한국어 브리핑 + top themes.
CREATE TABLE IF NOT EXISTS daily_overviews (
    date        DATE PRIMARY KEY,
    overview_text TEXT NOT NULL,
    top_themes  JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
