from app.bootstrap import NOTICE_SOURCES
from app.crawlers.notice_crawler import GO_MAX_PAGES, MANGBOARD_MAX_PAGES


def test_rss_sources_use_row_100():
    rss_sources = {s["name"]: s["rss_url"] for s in NOTICE_SOURCES if s.get("rss_url")}
    assert "row=100" in rss_sources["cse_notice"]
    assert "row=100" in rss_sources["grad_notice"]
    assert "row=100" in rss_sources["ai_notice"]
    assert "row=100" in rss_sources["bk4_notice"]
    assert "row=100" in rss_sources["bk4_repo"]


def test_non_rss_sources_keep_html_mode():
    conf = {s["name"]: s for s in NOTICE_SOURCES}
    assert conf["go_grad_notice"]["rss_url"] is None
    assert conf["aisec_notice"]["rss_url"] is None
    assert conf["go_grad_notice"]["crawl_mode"] == "go_board_html"
    assert conf["aisec_notice"]["crawl_mode"] == "mangboard_html"


def test_go_and_mangboard_forced_to_one_page():
    assert GO_MAX_PAGES == 1
    assert MANGBOARD_MAX_PAGES == 1
