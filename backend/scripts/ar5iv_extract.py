"""arXiv 논문 본문을 HTML로 가져와 섹션별 텍스트로 정리.

PDF 다운로드를 피해 디스크/네트워크 비용 절감:
- 1차: ar5iv.labs.arxiv.org/html/<id>  (가장 깔끔한 변환)
- 2차: arxiv.org/html/<id>             (arXiv 공식 HTML, 최신 논문 fallback)
- 3차: 둘 다 실패 → None 반환 (호출자가 PDF fallback 또는 skip 결정)

LLM에 주입할 섹션만 추출: abstract, introduction, method, experiments, conclusion.
related work / appendix / references / acknowledgments는 제외.
"""
from __future__ import annotations
import re
import requests
from html.parser import HTMLParser

HEADERS = {'User-Agent': 'HotPaper/1.0 (https://hotpaper.ai)'}

# 유지할 섹션 (소문자 매칭). related work / appendix 등은 제외.
KEEP_SECTION_RE = re.compile(
    r'^(abstract|introduction|background|preliminaries|'
    r'method|methods|methodology|approach|model|architecture|framework|'
    r'experiment|experiments|evaluation|results|analysis|ablation|'
    r'discussion|conclusion|conclusions)'
    r'(\s|\d|$)',
    re.I,
)
DROP_SECTION_RE = re.compile(
    r'^(related\s*work|references|bibliography|acknowledg|'
    r'appendix|supplement|broader\s*impact|ethics\s*statement|'
    r'reproducibility|limitations)'
    r'(\s|\d|$)',
    re.I,
)


class _SectionParser(HTMLParser):
    """ar5iv / arxiv.org HTML 둘 다 처리. <h1>-<h6>로 section 경계, <p>로 본문."""
    def __init__(self):
        super().__init__()
        self.sections: list[dict] = []
        self.current: dict | None = None
        self._in_header: int | None = None
        self._header_text: list[str] = []
        self._in_para = False
        self._para_text: list[str] = []
        self._skip_until: str | None = None  # tag 이름 (e.g. 'cite', 'script')

    def handle_starttag(self, tag, attrs):
        if self._skip_until:
            return
        if tag in ('script', 'style', 'cite'):
            self._skip_until = tag
            return
        if tag in ('h1','h2','h3','h4','h5','h6'):
            self._in_header = int(tag[1])
            self._header_text = []
        elif tag == 'p':
            self._in_para = True
            self._para_text = []

    def handle_endtag(self, tag):
        if self._skip_until == tag:
            self._skip_until = None
            return
        if tag in ('h1','h2','h3','h4','h5','h6') and self._in_header is not None:
            title = ' '.join(self._header_text).strip()
            # 번호 prefix 제거: "3.1 Method" → "Method"
            title_clean = re.sub(r'^[\d\.]+\s*', '', title)
            self._start_new_section(title_clean)
            self._in_header = None
        elif tag == 'p' and self._in_para:
            text = ' '.join(self._para_text).strip()
            if self.current is not None and text:
                self.current['paragraphs'].append(text)
            self._in_para = False

    def handle_data(self, data):
        if self._skip_until:
            return
        if self._in_header is not None:
            self._header_text.append(data)
        elif self._in_para:
            self._para_text.append(data)

    def _start_new_section(self, title: str):
        if not title:
            return
        self.current = {'title': title, 'paragraphs': []}
        self.sections.append(self.current)


def _fetch_html(arxiv_id: str) -> str | None:
    """ar5iv 1차, arxiv.org/html 2차 fallback."""
    for url in (f'https://ar5iv.labs.arxiv.org/html/{arxiv_id}',
                f'https://arxiv.org/html/{arxiv_id}'):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if r.status_code == 200 and len(r.text) > 5000:
                # ar5iv가 redirect 시 abstract 페이지로 가는 경우 본문 X
                if 'ltx_para' in r.text or '<section' in r.text.lower():
                    return r.text
        except Exception:
            continue
    return None


def extract_paper_text(arxiv_id: str, max_chars_per_section: int = 6000) -> dict | None:
    """본문 텍스트를 섹션별 dict로 반환. 못 가져오면 None.

    Returns:
        {
          'arxiv_id': str,
          'sections': [{'title': str, 'text': str}, ...],   # keep만
          'total_chars': int,
          'source': 'ar5iv' | 'arxiv_html',
        }
    """
    html = _fetch_html(arxiv_id)
    if not html:
        return None

    parser = _SectionParser()
    try:
        parser.feed(html)
    except Exception:
        return None

    kept: list[dict] = []
    for s in parser.sections:
        title = s['title']
        if DROP_SECTION_RE.match(title):
            continue
        if not KEEP_SECTION_RE.match(title) and title.lower() != 'abstract':
            continue
        text = '\n\n'.join(s['paragraphs'])
        # 너무 긴 섹션은 앞부분만
        if len(text) > max_chars_per_section:
            text = text[:max_chars_per_section] + '...[truncated]'
        if text.strip():
            kept.append({'title': title, 'text': text})

    if not kept:
        return None

    return {
        'arxiv_id': arxiv_id,
        'sections': kept,
        'total_chars': sum(len(s['text']) for s in kept),
        'source': 'ar5iv' if 'ar5iv' in (html[:500] or '') else 'arxiv_html',
    }


def format_for_llm(paper: dict, max_total_chars: int = 18000) -> str:
    """LLM prompt에 넣을 형태로 직렬화. 토큰 budget 안에 맞춤."""
    parts = []
    used = 0
    for s in paper['sections']:
        chunk = f"## {s['title']}\n{s['text']}\n"
        if used + len(chunk) > max_total_chars:
            chunk = chunk[: max_total_chars - used] + '...[truncated]'
            parts.append(chunk)
            break
        parts.append(chunk)
        used += len(chunk)
    return '\n'.join(parts)


if __name__ == '__main__':
    import sys, json
    aid = sys.argv[1] if len(sys.argv) > 1 else '2603.27412'
    paper = extract_paper_text(aid)
    if not paper:
        print(f'❌ {aid}: HTML 추출 실패')
        sys.exit(1)
    print(f"✅ {aid} ({paper['source']}, {paper['total_chars']} chars, {len(paper['sections'])} sections)")
    for s in paper['sections']:
        print(f"  - {s['title']}: {len(s['text'])} chars")
    print()
    print('=== formatted for LLM (first 2000 chars) ===')
    print(format_for_llm(paper)[:2000])
