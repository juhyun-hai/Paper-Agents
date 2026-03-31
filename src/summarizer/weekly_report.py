import os
from datetime import datetime, timedelta
from typing import Dict, Any

from src.database import PaperDBManager
from src.recommender.trend_recommender import TrendAnalyzer
from src.utils.logger import get_logger
from src.utils.config import load_config

logger = get_logger(__name__)


class WeeklyReporter:
    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.db = PaperDBManager(self.config["database"]["path"])
        self.trend_analyzer = TrendAnalyzer(db_manager=self.db, config=self.config)

    def generate_report(self) -> str:
        now = datetime.now()
        week_num = now.isocalendar()[1]
        year = now.year
        report_name = f"weekly-{year}-W{week_num:02d}"
        logger.info(f"Generating weekly report: {report_name}")
        summary = self.trend_analyzer.get_weekly_summary()
        content = self._format_report(report_name, summary, now)
        summaries_path = self.config["obsidian"]["summaries_path"]
        os.makedirs(summaries_path, exist_ok=True)
        report_path = os.path.join(summaries_path, f"{report_name}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Weekly report saved: {report_path}")
        return report_path

    def _format_report(self, name: str, summary: Dict[str, Any], now: datetime) -> str:
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        week_end = now.strftime("%Y-%m-%d")
        total = summary.get("total_papers", 0)
        cat_stats = summary.get("category_stats", {})
        trending = summary.get("trending_papers", [])
        keywords = summary.get("trending_keywords", {})
        lines = [
            f"# Weekly Paper Report — {name}",
            f"**Period**: {week_start} ~ {week_end}",
            f"**Total papers in DB**: {total}",
            "",
            "## 📊 Category Statistics",
            "",
        ]
        for cat, count in list(cat_stats.items())[:10]:
            lines.append(f"- **{cat}**: {count} papers")
        lines += [
            "",
            "## 🔥 Trending Papers (Last 7 Days)",
            "",
        ]
        for p in trending[:10]:
            arxiv_id = p.get("arxiv_id", "")
            title = p.get("title", "")
            date = p.get("date", "")
            lines.append(f"- [[{arxiv_id}]] {title} ({date})")
        lines += [
            "",
            "## 📈 Trending Keywords",
            "",
        ]
        for kw, count in list(keywords.items())[:15]:
            lines.append(f"- **{kw}**: {count} mentions")
        lines += [
            "",
            "## 💡 Notes",
            "(주간 분석 메모 공간)",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    reporter = WeeklyReporter()
    path = reporter.generate_report()
    print(f"Report saved: {path}")
