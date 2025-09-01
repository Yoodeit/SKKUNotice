import scrapy
import re
from datetime import date, datetime
from parsel import Selector
# from urllib.parse import urljoin  # 사용 안 하니 주석
from ..items import UniNoticeItem  # ← 실제 items.py에 맞춰주세요

# 2025.08.28 / 2025-08-28 / 2025/08/28 대응
DATE_RX = re.compile(r"(\d{4})[.\-\/](\d{1,2})[.\-\/](\d{1,2})")

def parse_date_from_text(s: str) -> date | None:
    if not s:
        return None
    m = DATE_RX.search(s)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None

class UniNoticeStep4Spider(scrapy.Spider):
    name = "notice_step4"
    start_urls = ["https://www.skku.edu/skku/campus/skk_comm/notice01.do"]

    def __init__(self, date_from=None, date_to=None, include_undated="yes", *args, **kwargs):
        """
        사용 예:
          scrapy crawl notice_step4 -O out.jsonl -a date_from=2025-08-01 -a date_to=2025-08-31
          scrapy crawl notice_step4 -O out.jsonl -a include_undated=no
        """
        super().__init__(*args, **kwargs)
        self.date_from = self._parse_cli_date(date_from)
        self.date_to   = self._parse_cli_date(date_to)
        self.include_undated = str(include_undated).lower() in {"y","yes","true","1"}
        if date_from and not self.date_from:
            self.logger.warning("date_from 형식이 올바르지 않습니다(YYYY-MM-DD): %r", date_from)
        if date_to and not self.date_to:
            self.logger.warning("date_to 형식이 올바르지 않습니다(YYYY-MM-DD): %r", date_to)

    # ---------------- 목록 ----------------
    def parse(self, response):
        rows = response.css("ul.board-list-wrap > li")
        self.logger.info("li 개수: %d", len(rows))

        for row in rows:
            # 1) 상세 링크 (여러 패턴 허용)
            href = row.css(
                "dl > dt > a[title='자세히 보기']::attr(href)"
                #"dl > dt > a[href*='articleNo']::attr(href), "
                #"dl dt a[href^='?mode=view']::attr(href)"
            ).get()
            if not href:
                continue

            # 2) 제목 정제
            #raw_texts = row.css("dl > dt > a ::text").getall()
            title = row.css("dl > dt > a::text").get(default="").strip()


            # 3) 날짜 추출 (우선: dd 내 3번째 li, 다음: dt 내 3번째 li, 마지막: 정규식 스캔)
            date_text = (
                row.css("dl > dd.board-list-content-info > ul > li:nth-of-type(3) ::text").get()
            ).strip()

            posted_date = parse_date_from_text(date_text)
            

            # 4) 날짜 필터링 (date 객체로 비교)
            if self._out_of_range(posted_date):
                continue

            posted_at = posted_date.isoformat() if posted_date else None

            # 5) 상세로 이동
            yield response.follow(
                href,
                callback=self.parse_detail,
                meta={"title": title, "posted_at": posted_at}
            )

    # ---------------- 상세 ----------------
    def parse_detail(self, response):
        content_html = (
            response.css(
                ".board-view .content, .board_view .content, "
                ".bbs_view, .article, .post-content, .view .content, "
                "#content .view, #content .article, div.content"
            ).get()
            or ""
        )
        if not content_html:
            self.logger.warning("본문 선택자 미스: %s", response.url)

        text = self.extract_clean_text(content_html)

        item = UniNoticeItem()
        item["title"] = (response.meta.get("title") or "").strip()
        item["url"] = response.url
        item["posted_at"] = response.meta.get("posted_at")   # ISO 문자열 또는 None
        item["content"] = text
        item["attachments"] = []  # 4-6에서 채움
        yield item

    # ---------------- 헬퍼 ----------------
    def _parse_cli_date(self, s: str | None) -> date | None:
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    def _out_of_range(self, posted: date | None) -> bool:
        """True면 제외. 날짜가 없을 때는 include_undated에 따름(기본 포함)."""
        if posted is None:
            return not self.include_undated
        if self.date_from and posted < self.date_from:
            return True
        if self.date_to and posted > self.date_to:
            return True
        return False

    def extract_clean_text(self, html: str) -> str:
        if not html:
            return ""
        import re
        html = re.sub(r"(?i)<br\s*/?>", "\n", html)
        html = re.sub(r"(?i)</p\s*>", "\n", html)
        html = re.sub(r"(?i)</li\s*>", "\n", html)
        html = re.sub(r"(?i)</tr\s*>", "\n", html)
        sel = Selector(text=html)
        parts = sel.xpath("//text()[not(ancestor::script) and not(ancestor::style)]").getall()
        text = "\n".join(s.strip() for s in parts if s and s.strip())
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

