-- Saved searches — 사용자가 키워드/tag 등록 → 매일 매칭 paper 모음.
-- 이메일 발송은 별도 cron (다음 단계). 일단 데이터 모델.

CREATE TABLE IF NOT EXISTS saved_searches (
  id BIGSERIAL PRIMARY KEY,
  -- 사용자 식별: 계정 시스템 없으니 client-generated UUID (브라우저 저장)
  client_id VARCHAR(64) NOT NULL,
  email VARCHAR(255),  -- optional, 이메일 digest 원할 때만
  -- 검색 정의 (둘 중 하나 이상 채워짐)
  keyword TEXT,                  -- 자유 검색어
  tag VARCHAR(80),               -- 정확한 tag name (concepts.name)
  category VARCHAR(40),          -- arxiv category prefix (예: 'cs.LG')
  name VARCHAR(200) NOT NULL,    -- 사용자 라벨 (예: "VLA 논문")
  -- 알림 빈도
  frequency VARCHAR(16) NOT NULL DEFAULT 'daily',  -- daily | weekly | off
  -- 매칭 결과 추적 — 같은 paper를 중복 전송 안 함
  last_matched_at TIMESTAMPTZ,
  last_seen_arxiv_ids JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (keyword IS NOT NULL OR tag IS NOT NULL OR category IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS saved_searches_client_idx ON saved_searches(client_id);
CREATE INDEX IF NOT EXISTS saved_searches_email_idx ON saved_searches(email) WHERE email IS NOT NULL;
