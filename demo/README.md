# HotPaper Demo

강연 청중이 자기 노트북에서 5분 안에 봄.

## 1줄 실행

```bash
docker compose -f docker-compose.demo.yml up
```

3분 후:
- http://localhost:5174 — 사이트
- http://localhost:8001/docs — API swagger

## 무엇이 다른지

| | 운영 | Demo |
|---|---|---|
| LLM | Ollama qwen3:32b/14b | 없음 (요약은 미리 dump됨) |
| Cron | 03시 + 04시 자동 | 없음 (static seed) |
| DB | 7000+ paper | 200편 seed |
| Cloudflare | hotpaper.ai | localhost:8001 |
| HAI plugin | enabled | disabled |
| Volume | persistent | ephemeral |

## Seed 만들기 (운영 → demo dump)

```bash
# 운영 DB에서 최근 7일 featured + 요약 추출 → seed.sql
python scripts/make_demo_seed.py --days 7 --out demo/seed.sql
```

→ TODO: `scripts/make_demo_seed.py` 작성 (별도 commit)

## 종료

```bash
docker compose -f docker-compose.demo.yml down
```
