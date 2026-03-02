from app.crawlers.meal_crawler import _extract_available_restaurants, _parse_menu_table


def test_extract_available_restaurants():
    html = """
    <div id="childTab">
      <a href="#tmp" onclick="goSearchMenu( 'PUSAN', 'R001', 'PG001', '' );"><span>금정회관 교직원 식당</span></a>
      <a href="#tmp" onclick="goSearchMenu( 'PUSAN', 'R001', 'PG002', '' );"><span>금정회관 학생 식당</span></a>
    </div>
    """
    out = _extract_available_restaurants(html)
    assert out["PG001"] == "금정회관 교직원 식당"
    assert out["PG002"] == "금정회관 학생 식당"


def test_parse_menu_table_month_filter_and_rows():
    html = """
    <table class="menu-tbl type-day">
      <thead>
        <tr>
          <th>구분</th>
          <th><div class="date">2026.03.02</div></th>
          <th><div class="date">2026.03.03</div></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>중식</th>
          <td><ul><li><h3>정식</h3><p>메뉴A</p></li></ul></td>
          <td><ul><li><h3>정식</h3><p>메뉴B</p></li></ul></td>
        </tr>
        <tr>
          <th>석식</th>
          <td><ul></ul></td>
          <td><ul><li><p>야식</p></li></ul></td>
        </tr>
      </tbody>
    </table>
    """
    out = _parse_menu_table(html, cafeteria_key="student_hall", cafeteria_name="학생회관 학생 식당", month="2026-03")
    assert len(out) == 3
    assert out[0]["meal_type"] == "lunch"
    assert out[0]["cafeteria_key"] == "student_hall"
    assert out[1]["menu"].endswith("메뉴B")
