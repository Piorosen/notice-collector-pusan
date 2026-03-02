from datetime import date

from app.crawlers.calendar_crawler import categorize_event, parse_calendar_html, parse_date_range


def test_parse_date_range_range():
    start, end = parse_date_range("2026.03.02 ~ 2026.03.08")
    assert start == date(2026, 3, 2)
    assert end == date(2026, 3, 8)


def test_parse_date_range_single():
    start, end = parse_date_range("2026-04-01")
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 1)


def test_parse_calendar_html():
    html = """
    <table class='artclTable'>
      <tbody>
        <tr><td>2026.03.02 ~ 2026.03.08</td><td>수강정정 기간</td></tr>
        <tr><td>2026.06.20</td><td>기말시험 종료</td></tr>
      </tbody>
    </table>
    """
    events = parse_calendar_html(html)
    assert len(events) == 2
    assert events[0]["category"] == "enroll"
    assert events[1]["category"] == "exam"


def test_categorize_fallback():
    assert categorize_event("기타행사") == "general"
