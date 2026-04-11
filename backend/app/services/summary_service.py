"""
Paper Summary Service - PDF processing and AI-powered summarization.
"""

import os
import asyncio
import tempfile
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path
import requests
from urllib.parse import urljoin

import fitz  # PyMuPDF
from PIL import Image
import io

from ..ai.llm_client import get_default_client
from ..models import Paper
from ..core.database import AsyncSessionLocal
from sqlalchemy import select


class PaperSummaryService:
    """Generate comprehensive paper summaries with figures."""

    def __init__(self):
        self.llm_client = None  # Will be initialized when needed
        self.temp_dir = Path(tempfile.gettempdir()) / "paper_summaries"
        self.temp_dir.mkdir(exist_ok=True)

    async def _get_llm_client(self):
        """Get LLM client, initializing if needed."""
        if self.llm_client is None:
            self.llm_client = await get_default_client()
        return self.llm_client

    async def generate_summary(self, arxiv_id: str) -> Dict[str, Any]:
        """Generate comprehensive summary for a paper."""
        print(f"📄 Generating summary for {arxiv_id}")

        try:
            # Get paper from database
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Paper).where(Paper.arxiv_id == arxiv_id)
                )
                paper = result.scalar_one_or_none()

                if not paper:
                    raise ValueError(f"Paper {arxiv_id} not found")

            # Download and process PDF
            pdf_path = await self._download_pdf(arxiv_id)
            if not pdf_path:
                return await self._generate_abstract_only_summary(paper)

            # Extract text and figures
            full_text = self._extract_text_from_pdf(pdf_path)
            figures = self._extract_figures_from_pdf(pdf_path, arxiv_id)

            # Generate AI summary
            summary_data = await self._generate_ai_summary(
                paper, full_text, figures
            )

            # Clean up
            if pdf_path.exists():
                pdf_path.unlink()

            return summary_data

        except Exception as e:
            print(f"❌ Summary generation failed: {e}")
            # Fallback to abstract-only summary
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Paper).where(Paper.arxiv_id == arxiv_id)
                )
                paper = result.scalar_one_or_none()
                return await self._generate_abstract_only_summary(paper)

    async def _download_pdf(self, arxiv_id: str) -> Optional[Path]:
        """Download PDF from arXiv."""
        try:
            # arXiv PDF URL format
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            print(f"📥 Downloading PDF from {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            # Save to temp file
            pdf_path = self.temp_dir / f"{arxiv_id}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(response.content)

            print(f"✅ PDF downloaded: {pdf_path}")
            return pdf_path

        except Exception as e:
            print(f"❌ PDF download failed: {e}")
            return None

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text content from PDF."""
        try:
            doc = fitz.open(str(pdf_path))
            full_text = ""

            for page_num in range(min(20, len(doc))):  # Limit to first 20 pages
                page = doc.load_page(page_num)
                text = page.get_text()
                full_text += f"\n--- Page {page_num + 1} ---\n{text}"

            doc.close()
            print(f"📝 Extracted {len(full_text)} characters from PDF")
            return full_text

        except Exception as e:
            print(f"❌ Text extraction failed: {e}")
            return ""

    def _extract_figures_from_pdf(self, pdf_path: Path, arxiv_id: str) -> List[Dict[str, Any]]:
        """Extract figures and diagrams from PDF."""
        figures = []
        try:
            doc = fitz.open(str(pdf_path))

            for page_num in range(min(10, len(doc))):  # First 10 pages for figures
                page = doc.load_page(page_num)

                # Get images on this page
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    if len(figures) >= 10:  # Limit to 10 figures
                        break

                    try:
                        # Extract image
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        # Skip very small images (likely icons/logos)
                        if pix.width < 100 or pix.height < 100:
                            pix = None
                            continue

                        # Convert to PNG bytes
                        if pix.n < 5:  # GRAY or RGB
                            img_bytes = pix.tobytes("png")
                        else:  # CMYK
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            img_bytes = pix1.tobytes("png")
                            pix1 = None

                        # Encode as base64 for web display
                        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

                        figures.append({
                            "id": f"fig_{page_num+1}_{img_index+1}",
                            "page": page_num + 1,
                            "width": pix.width,
                            "height": pix.height,
                            "data": img_b64,
                            "caption": f"Figure from page {page_num + 1}"
                        })

                        pix = None

                    except Exception as e:
                        print(f"⚠️ Failed to extract image: {e}")
                        continue

            doc.close()
            print(f"🖼️ Extracted {len(figures)} figures")
            return figures

        except Exception as e:
            print(f"❌ Figure extraction failed: {e}")
            return []

    async def _generate_ai_summary(
        self,
        paper: Paper,
        full_text: str,
        figures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate AI-powered comprehensive summary."""

        # Create comprehensive prompt
        prompt = f"""
당신은 AI/ML 논문을 분석하고 블로그 스타일의 요약을 작성하는 전문가입니다.

논문 정보:
- 제목: {paper.title}
- 저자: {', '.join(paper.authors or [])}
- arXiv ID: {paper.arxiv_id}
- 카테고리: {', '.join(paper.categories or [])}
- 초록: {paper.abstract}

{"PDF 전문:" if full_text else "PDF를 읽을 수 없어 초록만 사용:"}
{full_text[:8000] if full_text else "PDF 내용 없음"}

다음과 같은 구조로 블로그 스타일 요약을 작성해주세요:

## 📋 한 줄 요약
(논문의 핵심을 한 문장으로)

## 🎯 핵심 기여도
- 주요 기여점 3-4개를 불릿 포인트로

## 💡 핵심 아이디어
(논문의 주요 아이디어를 일반인도 이해할 수 있게 설명)

## 🔬 기술적 접근법
- **모델 구조**:
- **핵심 알고리즘**:
- **훈련 방법**:

## 📊 주요 결과
(성능, 벤치마크 결과 등)

## 🔍 실험 및 평가
- **데이터셋**:
- **평가 지표**:
- **비교 대상**:

## 💭 의의 및 한계
**의의**:
-

**한계**:
-

## 🚀 응용 가능성
(이 연구가 실제로 어떻게 활용될 수 있는지)

## 📚 관련 연구와의 차이점
(기존 연구 대비 새로운 점)

---

응답은 반드시 마크다운 형태로, 이모지를 포함하여 블로그 글처럼 작성해주세요.
기술적인 내용도 포함하되, 일반인도 이해할 수 있도록 쉽게 설명해주세요.
"""

        try:
            # Generate summary using LLM
            llm_client = await self._get_llm_client()
            summary_text = await llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.3
            )

            return {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_text": summary_text,
                "figures": figures,
                "generated_at": "2026-04-06T00:00:00Z",
                "summary_type": "comprehensive" if full_text else "abstract_only"
            }

        except Exception as e:
            print(f"❌ AI summary generation failed: {e}")
            return await self._generate_abstract_only_summary(paper)

    async def _generate_abstract_only_summary(self, paper: Paper) -> Dict[str, Any]:
        """Generate summary based on abstract only."""
        prompt = f"""
논문의 초록만을 바탕으로 간단한 요약을 작성해주세요.

논문 정보:
- 제목: {paper.title}
- 저자: {', '.join(paper.authors or [])}
- 초록: {paper.abstract}

다음 형태로 요약해주세요:

## 📋 논문 개요
{paper.title}

## 🎯 핵심 내용
(초록 기반으로 주요 내용 정리)

## 💡 연구 방법
(초록에서 언급된 방법론)

## 📊 기대 효과
(초록에서 언급된 결과나 기여도)

---
※ 이 요약은 초록만을 바탕으로 생성되었습니다. 더 자세한 내용은 원문을 참조해주세요.
"""

        try:
            llm_client = await self._get_llm_client()
            summary_text = await llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3
            )

            return {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_text": summary_text,
                "figures": [],
                "generated_at": "2026-04-06T00:00:00Z",
                "summary_type": "abstract_only"
            }

        except Exception as e:
            print(f"❌ Abstract summary failed: {e}")
            return {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors or [],
                "summary_text": f"## {paper.title}\n\n{paper.abstract}\n\n*요약 생성에 실패했습니다.*",
                "figures": [],
                "generated_at": "2026-04-06T00:00:00Z",
                "summary_type": "fallback"
            }


# Global service instance
_summary_service = None

def get_summary_service() -> PaperSummaryService:
    """Get or create summary service instance."""
    global _summary_service
    if _summary_service is None:
        _summary_service = PaperSummaryService()
    return _summary_service