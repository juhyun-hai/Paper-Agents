#!/usr/bin/env python3
"""
일일/주간 다이제스트 생성 스크립트

Usage:
    python scripts/generate_daily_digest.py --type daily
    python scripts/generate_daily_digest.py --type weekly
    python scripts/generate_daily_digest.py --type both
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import PaperDBManager
from src.trend_analyzer import TrendAnalyzer
from src.utils.logger import get_logger

logger = get_logger(__name__)


def save_digest_to_file(digest: dict, digest_type: str, output_dir: str = "data/digests"):
    """다이제스트를 파일로 저장"""
    os.makedirs(output_dir, exist_ok=True)

    date_str = digest.get('date') or digest.get('week_ending', datetime.now().strftime("%Y-%m-%d"))
    filename = f"{digest_type}_digest_{date_str}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)

    logger.info(f"📄 {digest_type.title()} digest saved: {filepath}")
    return filepath


def generate_markdown_digest(digest: dict, digest_type: str) -> str:
    """다이제스트를 마크다운으로 변환"""
    if digest_type == 'daily':
        date = digest['date']
        md_lines = [
            f"# Daily Research Digest - {date}",
            "",
            f"생성일시: {digest['generated_at']}",
            "",
            "## 📊 요약",
            f"- 분석된 키워드: {digest['summary']['total_papers_analyzed']}개",
            f"- Hot Topics: {digest['summary']['hot_topics_count']}개",
            f"- Emerging Tech: {digest['summary']['emerging_tech_count']}개",
            f"- Must-Know: {digest['summary']['must_know_count']}개",
            f"- Citation Surges: {digest['summary']['citation_surges_count']}개",
            "",
        ]

        # Hot Topics
        if digest['classifications']['hot_topics']:
            md_lines.extend([
                "## 🔥 Hot Topics",
                ""
            ])
            for topic in digest['classifications']['hot_topics']:
                md_lines.append(
                    f"- **{topic['keyword']}** (트렌드 스코어: {topic['trend_score']}, "
                    f"논문 수: {topic['recent_papers']}, 인용 속도: {topic['citation_velocity']})"
                )
            md_lines.append("")

        # Emerging Tech
        if digest['classifications']['emerging_tech']:
            md_lines.extend([
                "## 🌟 Emerging Technology",
                ""
            ])
            for topic in digest['classifications']['emerging_tech']:
                md_lines.append(
                    f"- **{topic['keyword']}** (트렌드 스코어: {topic['trend_score']}, "
                    f"논문 수: {topic['recent_papers']}, 잠재력: {topic['potential']})"
                )
            md_lines.append("")

        # Must-Know
        if digest['classifications']['must_know']:
            md_lines.extend([
                "## 📚 Must-Know",
                ""
            ])
            for topic in digest['classifications']['must_know']:
                md_lines.append(
                    f"- **{topic['keyword']}** (평균 인용: {topic['avg_citations']}, "
                    f"논문 수: {topic['paper_count']}, 안정성: {topic['stability']})"
                )
            md_lines.append("")

        # Citation Surges
        if digest['citation_surges']:
            md_lines.extend([
                "## 📈 Citation Surges",
                ""
            ])
            for paper in digest['citation_surges'][:5]:
                md_lines.append(
                    f"- [{paper['arxiv_id']}] {paper['title'][:60]}... "
                    f"(인용: {paper['citation_count']}회)"
                )
            md_lines.append("")

        # Research Flow
        if digest['research_flow']['summary']:
            md_lines.extend([
                "## 🔄 Research Flow Changes",
                "",
                digest['research_flow']['summary'],
                ""
            ])

    elif digest_type == 'weekly':
        date = digest['week_ending']
        md_lines = [
            f"# Weekly Research Digest - Week ending {date}",
            "",
            f"생성일시: {digest['generated_at']}",
            "",
            "## 📊 주간 요약",
            f"- 추적된 키워드: {digest['summary']['total_tracked_keywords']}개",
            f"- 지속적 트렌드: {digest['summary']['persistent_trends']}개",
            f"- 분석 기간: {digest['summary']['analysis_days']}일",
            "",
        ]

        # Top Weekly Trends
        if digest['top_weekly_trends']:
            md_lines.extend([
                "## 📈 주간 Top 트렌드",
                ""
            ])
            for trend in digest['top_weekly_trends'][:10]:
                md_lines.append(
                    f"- **{trend['keyword']}** ({trend['category']}) - "
                    f"지속성: {trend['consistency_score']}일, "
                    f"평균 스코어: {trend['avg_trend_score']} "
                    f"({trend['persistence']})"
                )
            md_lines.append("")

        # Insights
        if digest['trend_insights']:
            md_lines.extend([
                "## 💡 주요 인사이트",
                ""
            ])
            for insight in digest['trend_insights']:
                md_lines.append(f"- {insight}")
            md_lines.append("")

    return "\n".join(md_lines)


def main():
    parser = argparse.ArgumentParser(description="Generate daily/weekly research digests")
    parser.add_argument('--type', choices=['daily', 'weekly', 'both'], default='daily',
                        help="Type of digest to generate")
    parser.add_argument('--date', help="Specific date (YYYY-MM-DD) for daily digest")
    parser.add_argument('--output-dir', default="data/digests",
                        help="Output directory for digest files")
    parser.add_argument('--markdown', action='store_true',
                        help="Also generate markdown versions")
    parser.add_argument('--quiet', action='store_true',
                        help="Suppress output messages")

    args = parser.parse_args()

    if not args.quiet:
        print("🔍 Initializing trend analyzer...")

    # Initialize
    db = PaperDBManager()
    analyzer = TrendAnalyzer(db)

    results = []

    if args.type in ['daily', 'both']:
        if not args.quiet:
            print("📅 Generating daily digest...")

        try:
            daily_digest = analyzer.generate_daily_digest(args.date)

            # Save JSON
            json_path = save_digest_to_file(daily_digest, 'daily', args.output_dir)
            results.append(f"Daily JSON: {json_path}")

            # Save Markdown if requested
            if args.markdown:
                md_content = generate_markdown_digest(daily_digest, 'daily')
                md_filename = f"daily_digest_{daily_digest['date']}.md"
                md_path = os.path.join(args.output_dir, md_filename)
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                results.append(f"Daily MD: {md_path}")

            if not args.quiet:
                print(f"✅ Daily digest completed for {daily_digest['date']}")
                print(f"   📊 {daily_digest['summary']['hot_topics_count']} hot topics, "
                      f"{daily_digest['summary']['emerging_tech_count']} emerging tech")

        except Exception as e:
            logger.error(f"Daily digest generation failed: {e}")
            if not args.quiet:
                print(f"❌ Daily digest failed: {e}")

    if args.type in ['weekly', 'both']:
        if not args.quiet:
            print("📅 Generating weekly digest...")

        try:
            weekly_digest = analyzer.generate_weekly_digest()

            # Save JSON
            json_path = save_digest_to_file(weekly_digest, 'weekly', args.output_dir)
            results.append(f"Weekly JSON: {json_path}")

            # Save Markdown if requested
            if args.markdown:
                md_content = generate_markdown_digest(weekly_digest, 'weekly')
                md_filename = f"weekly_digest_{weekly_digest['week_ending']}.md"
                md_path = os.path.join(args.output_dir, md_filename)
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                results.append(f"Weekly MD: {md_path}")

            if not args.quiet:
                print(f"✅ Weekly digest completed for week ending {weekly_digest['week_ending']}")
                print(f"   📈 {len(weekly_digest['top_weekly_trends'])} top trends, "
                      f"{weekly_digest['summary']['persistent_trends']} persistent")

        except Exception as e:
            logger.error(f"Weekly digest generation failed: {e}")
            if not args.quiet:
                print(f"❌ Weekly digest failed: {e}")

    # Summary
    if not args.quiet and results:
        print("\n📁 Generated files:")
        for result in results:
            print(f"   {result}")

    return len(results) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)