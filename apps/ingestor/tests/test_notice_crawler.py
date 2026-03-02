from app.crawlers.notice_crawler import (
    _normalize_notice_link,
    _parse_go_list,
    _parse_mangboard_detail,
    _parse_mangboard_list,
)
from app.models import Source
from app.utils.url_normalize import normalize_source_url


def test_normalize_source_url_typo_fix():
    assert normalize_source_url(" https://cse.pusan.ac.kr/cse/14659/subvㅁiew.do ") == "https://cse.pusan.ac.kr/cse/14659/subview.do"


def test_parse_go_list_extract_js_board_view_id():
    html = """
    <table class='tb_type1'>
      <tr><th>헤더</th></tr>
      <tr>
        <td>1</td>
        <td class='al'><a href="javascript:js_board_view(49255);">공지 제목</a></td>
        <td>2026.02.13</td>
        <td>660</td>
      </tr>
    </table>
    """
    rows = _parse_go_list(html)
    assert len(rows) == 1
    assert rows[0]["bn"] == "49255"
    assert rows[0]["title"] == "공지 제목"
    assert rows[0]["date_raw"] == "2026.02.13"


def test_parse_mangboard_list_extract_vid_and_date():
    html = """
    <table>
      <tbody id="sub51_board_body">
        <tr>
          <td>34</td>
          <td class="text-left"><a href="https://aisec.pusan.ac.kr/?page_id=429&vid=34" title="제목">제목</a></td>
          <td>infosec</td>
          <td>2022-10-04</td>
        </tr>
      </tbody>
    </table>
    """
    rows = _parse_mangboard_list(html)
    assert len(rows) == 1
    assert rows[0]["vid"] == "34"
    assert rows[0]["author"] == "infosec"
    assert rows[0]["date_raw"] == "2022-10-04"


def test_parse_mangboard_detail_extract_content_and_meta():
    html = """
    <table class="table table-view">
      <tr id="mb_sub51_tr_title"><td><span style="float:right;width:155px;text-align:right;">2022-10-04 09:40</span></td></tr>
      <tr id="mb_sub51_tr_user_name"><td><span>infosec</span></td></tr>
      <tr id="mb_sub51_tr_content"><td class="content-box text-left" colspan="2"><p>본문 테스트</p><a href="/file/test.hwp">첨부</a></td></tr>
    </table>
    """
    body_html, body_text, attach_items, image_urls, date_raw, author = _parse_mangboard_detail(html, "https://aisec.pusan.ac.kr/?page_id=429&vid=34")
    assert "본문 테스트" in body_html
    assert "본문 테스트" in body_text
    assert len(attach_items) == 1
    assert attach_items[0][1].endswith("/file/test.hwp")
    assert image_urls == []
    assert date_raw == "2022-10-04 09:40"
    assert author == "infosec"


def test_normalize_notice_link_handles_relative_url():
    source = Source(
        name="ai_notice",
        source_type="notice",
        base_url="https://ai.pusan.ac.kr/ai/2907/subview.do",
        rss_url="https://ai.pusan.ac.kr/bbs/ai/204/rssList.do?row=100",
        crawl_mode="k2web_rss",
        active=True,
    )
    normalized = _normalize_notice_link("/bbs/ai/204/1044644/artclView.do?layout=unknown", source)
    assert normalized == "https://ai.pusan.ac.kr/bbs/ai/204/1044644/artclView.do?layout=unknown"
