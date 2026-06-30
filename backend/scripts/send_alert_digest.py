#!/usr/bin/env python3
"""매일 09시 KST cron: saved_searches 가입자에게 매칭 paper digest 발송.

설계:
- saved_searches.email 있고 frequency='daily' 인 row만
- 각 row의 매칭 paper 중 last_seen_arxiv_ids 에 없는 새 paper 만
- 한 사용자에게 여러 saved_search 매칭이 있으면 하나의 이메일로 묶음
- 발송 후 last_matched_at / last_seen_arxiv_ids 갱신

환경변수 (없으면 dry-run = 발송 안 함, stdout으로 미리보기):
  SMTP_HOST      smtp.gmail.com 등
  SMTP_PORT      587 (TLS) / 465 (SSL)
  SMTP_USER      발송자 계정
  SMTP_PASS      앱 비밀번호 (Gmail은 https://myaccount.google.com/apppasswords)
  SMTP_FROM      "HotPaper Digest <noreply@hotpaper.ai>"
  ALERT_DRY_RUN  '1' 강제 dry-run

사용:
  python scripts/send_alert_digest.py                  # 일반 daily
  ALERT_DRY_RUN=1 python scripts/send_alert_digest.py  # 미리보기

crontab 등록 권장:
  0 9 * * *  cd /.../backend && venv/bin/python -u scripts/send_alert_digest.py \
    >> logs/alert_digest.log 2>&1
"""
from __future__ import annotations
import asyncio
import json
import os
import smtplib
import sys
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncpg

DB_URL = 'postgresql://research_agent:research_pass_2024@localhost:5432/research_intelligence'
SITE_URL = 'https://hotpaper.ai'

SMTP_HOST = os.environ.get('SMTP_HOST', '').strip()
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '').strip()
SMTP_PASS = os.environ.get('SMTP_PASS', '').strip()
SMTP_FROM = os.environ.get('SMTP_FROM', '"HotPaper" <noreply@hotpaper.ai>').strip()
DRY_RUN = bool(int(os.environ.get('ALERT_DRY_RUN', '0'))) or not (SMTP_HOST and SMTP_USER)


async def match_one(conn, saved):
    """1개 saved_search의 새 매칭 paper (last_seen 제외)."""
    cutoff = date.today() - timedelta(days=7)
    seen = set(saved.get('last_seen_arxiv_ids') or [])
    conditions = ["p.published_date >= $1"]
    args = [cutoff]
    if saved['tag']:
        args.append(saved['tag'])
        conditions.append(f"""EXISTS (
            SELECT 1 FROM paper_concepts pc
            JOIN concepts c ON c.id = pc.concept_id
            WHERE pc.paper_id = p.id AND c.type='keyword' AND lower(c.name) = lower(${len(args)})
        )""")
    if saved['keyword']:
        args.append(f"%{saved['keyword']}%")
        conditions.append(f"(p.title ILIKE ${len(args)} OR p.abstract ILIKE ${len(args)})")
    if saved['category']:
        args.append(f"%{saved['category']}%")
        conditions.append(f"p.categories::text ILIKE ${len(args)}")
    sql = f"""
        SELECT p.arxiv_id, p.title, COALESCE(s.summary_text, '') AS summary,
               p.html_url
        FROM papers p
        LEFT JOIN paper_summaries s ON s.arxiv_id = p.arxiv_id
        WHERE {' AND '.join(conditions)}
        ORDER BY p.published_date DESC NULLS LAST
        LIMIT 30
    """
    rows = await conn.fetch(sql, *args)
    new = [dict(r) for r in rows if r['arxiv_id'] not in seen]
    return new


def render_email(email: str, by_search: dict) -> tuple[str, str, str]:
    """(subject, text_body, html_body) 생성."""
    n_total = sum(len(v) for v in by_search.values())
    subject = f"[HotPaper] {date.today():%Y-%m-%d} · 새 논문 {n_total}편"
    text_parts = [f"HotPaper Daily Digest — {date.today().isoformat()}", '']
    html_parts = [f"<h2>HotPaper Daily Digest — {date.today():%Y-%m-%d}</h2>"]
    for name, papers in by_search.items():
        if not papers:
            continue
        text_parts.append(f"\n## {name}  ({len(papers)}편)")
        html_parts.append(f"<h3>{name} <small>({len(papers)}편)</small></h3><ul>")
        for p in papers[:10]:
            text_parts.append(f"- {p['title']}  →  {SITE_URL}/paper/{p['arxiv_id']}")
            html_parts.append(
                f"<li><a href='{SITE_URL}/paper/{p['arxiv_id']}'>{p['title']}</a> "
                f"<small>({p['arxiv_id']})</small></li>"
            )
        if len(papers) > 10:
            text_parts.append(f"  … 외 {len(papers)-10}편")
            html_parts.append(f"<li><i>… 외 {len(papers)-10}편</i></li>")
        html_parts.append("</ul>")
    text_parts.append(f"\n— 알림 관리: {SITE_URL}/alerts")
    html_parts.append(
        f"<hr><p style='color:#888;font-size:12px'>"
        f"<a href='{SITE_URL}/alerts'>알림 관리</a> · "
        f"HotPaper.ai</p>"
    )
    return subject, '\n'.join(text_parts), '\n'.join(html_parts)


def send_smtp(to_email: str, subject: str, text_body: str, html_body: str):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_FROM, [to_email], msg.as_string())


async def main():
    conn = await asyncpg.connect(DB_URL)
    saved_rows = await conn.fetch("""
        SELECT * FROM saved_searches
        WHERE frequency = 'daily' AND email IS NOT NULL AND email != ''
        ORDER BY email, id
    """)
    print(f"📋 daily 가입자: {len(saved_rows)}개 saved_search")
    if not saved_rows:
        print("nothing to send"); await conn.close(); return

    by_email: dict[str, dict] = {}
    seen_updates = {}  # sid → new arxiv_ids to append
    for s in saved_rows:
        d = dict(s)
        new = await match_one(conn, d)
        if not new:
            continue
        by_email.setdefault(d['email'], {})[d['name']] = new
        seen_updates[d['id']] = [p['arxiv_id'] for p in new]
    print(f"📧 발송 대상 이메일: {len(by_email)}, dry_run={DRY_RUN}")

    for email, by_search in by_email.items():
        subject, text_body, html_body = render_email(email, by_search)
        if DRY_RUN:
            print(f"\n--- [DRY] to: {email} ---\n{subject}\n{text_body[:600]}\n...")
        else:
            try:
                send_smtp(email, subject, text_body, html_body)
                print(f"  ✅ sent: {email} ({sum(len(v) for v in by_search.values())}편)")
            except Exception as e:
                print(f"  ❌ {email}: {e}")
                continue

    # last_seen 갱신 (DRY 일 때는 안 함 — 다음 run에서 재시도)
    if not DRY_RUN:
        for sid, new_ids in seen_updates.items():
            await conn.execute("""
                UPDATE saved_searches SET
                  last_seen_arxiv_ids = COALESCE(last_seen_arxiv_ids,'[]'::jsonb) || $1::jsonb,
                  last_matched_at = NOW(), updated_at = NOW()
                WHERE id = $2
            """, json.dumps(new_ids), sid)
    await conn.close()
    print("Done.")


if __name__ == '__main__':
    asyncio.run(main())
