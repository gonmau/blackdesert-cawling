"""
generate_dashboard.py
data/crimson_desert_rivals.json → index.html 변환기
"""

import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("data/crimson_desert_rivals.json")
OUTPUT_FILE = Path("index.html")


def load_data() -> dict:
    if not DATA_FILE.exists():
        return {}
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def format_price(item: dict) -> str:
    if item.get("is_free"):
        return '<span class="badge free">FREE</span>'
    currency = item.get("currency", "")
    fp = item.get("final_price", 0)
    op = item.get("original_price")
    dp = item.get("discount_percent", 0)

    if dp > 0 and op:
        return f'<span class="price-orig">{currency} {op}</span> <span class="price-final">{currency} {fp}</span>'
    return f'<span class="price-final">{currency} {fp}</span>'


def discount_badge(pct: int) -> str:
    if pct <= 0:
        return ""
    color = "#ff4444" if pct >= 75 else "#ff8800" if pct >= 50 else "#22bb55"
    return f'<span class="badge disc" style="background:{color}">-{pct}%</span>'


def build_country_card(cc: str, data: dict) -> str:
    name = data.get("name", cc)
    rank = data.get("crimson_desert_rank")
    rivals = data.get("rivals", [])
    not_charted = data.get("not_charted", False)

    if not_charted or rank is None:
        status = "순위권 밖" if not_charted else "데이터 없음"
        return f"""
        <div class="country-card charted-no">
          <div class="country-header">
            <span class="country-name">{name}</span>
            <span class="rank-badge none">{status}</span>
          </div>
        </div>"""

    rival_rows = ""
    for r in rivals:
        dp = r.get("discount_percent", 0)
        is_free = r.get("is_free", False)
        row_class = "free-row" if is_free else "disc-row"
        rival_rows += f"""
        <tr class="{row_class}">
          <td class="rank-num">#{r['rank']}</td>
          <td class="game-name">
            <a href="{r.get('store_url','#')}" target="_blank">{r['name']}</a>
          </td>
          <td>{format_price(r)}</td>
          <td>{discount_badge(dp) if not is_free else ''}</td>
        </tr>"""

    rivals_section = f"""
      <div class="rivals-wrap">
        <table class="rivals-table">
          <thead><tr>
            <th>순위</th><th>게임</th><th>가격</th><th>할인</th>
          </tr></thead>
          <tbody>{rival_rows}</tbody>
        </table>
      </div>""" if rivals else '<p class="no-rival">상위 순위에 무료/할인 게임 없음</p>'

    rank_cls = "rank-top" if rank <= 10 else "rank-mid" if rank <= 30 else "rank-low"
    return f"""
    <div class="country-card">
      <div class="country-header">
        <span class="country-name">{name}</span>
        <span class="rank-badge {rank_cls}">붉은사막 {rank}위</span>
        <span class="rival-count">{len(rivals)}개 경쟁</span>
      </div>
      {rivals_section}
    </div>"""


def generate_html(data: dict) -> str:
    generated_at = data.get("generated_at", "")
    try:
        dt = datetime.strptime(generated_at, "%Y-%m-%dT%H:%M:%SZ")
        kst_str = dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        kst_str = generated_at

    countries = data.get("countries", {})

    # 통계
    charted = [v for v in countries.values() if not v.get("not_charted") and v.get("crimson_desert_rank")]
    total_rivals = sum(len(v.get("rivals", [])) for v in charted)
    avg_rank = round(sum(v["crimson_desert_rank"] for v in charted) / len(charted), 1) if charted else "-"
    best = min(charted, key=lambda v: v["crimson_desert_rank"], default=None)
    best_str = f"{best['name']} ({best['crimson_desert_rank']}위)" if best else "-"

    cards_html = "\n".join(build_country_card(cc, d) for cc, d in countries.items())

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>붉은사막 Steam 경쟁 트래커</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0c10;
    --surface: #111520;
    --border: #1e2535;
    --accent: #c84b31;
    --accent2: #e8a020;
    --text: #dce4f0;
    --muted: #6a7a90;
    --free: #22bb88;
    --disc: #e8a020;
    --top: #c84b31;
    --mid: #e8a020;
    --low: #4488cc;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans KR', sans-serif;
    min-height: 100vh;
  }}

  /* ── 헤더 ── */
  header {{
    background: linear-gradient(135deg, #0d0f18 0%, #1a0a08 100%);
    border-bottom: 1px solid var(--border);
    padding: 28px 32px 24px;
    position: relative;
    overflow: hidden;
  }}
  header::before {{
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(ellipse 60% 80% at 80% 50%, rgba(200,75,49,.12) 0%, transparent 70%);
  }}
  .header-inner {{ position: relative; max-width: 1400px; margin: 0 auto; }}
  .site-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2.4rem;
    letter-spacing: .05em;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .site-title span {{ color: var(--accent); }}
  .subtitle {{
    color: var(--muted);
    font-size: .85rem;
    margin-top: 4px;
  }}
  .updated {{ 
    position: absolute; right: 0; top: 4px;
    font-size: .75rem; color: var(--muted);
    background: rgba(255,255,255,.04);
    border: 1px solid var(--border);
    padding: 4px 10px; border-radius: 4px;
  }}

  /* ── 통계 바 ── */
  .stats-bar {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 32px;
  }}
  .stats-inner {{
    max-width: 1400px; margin: 0 auto;
    display: flex; gap: 32px; flex-wrap: wrap;
  }}
  .stat-item {{
    display: flex; flex-direction: column; gap: 2px;
  }}
  .stat-label {{ font-size: .72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
  .stat-value {{ font-size: 1.3rem; font-weight: 700; color: var(--accent2); }}

  /* ── 메인 그리드 ── */
  .main {{ max-width: 1400px; margin: 0 auto; padding: 28px 32px; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 16px;
  }}

  /* ── 국가 카드 ── */
  .country-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color .2s;
  }}
  .country-card:hover {{ border-color: rgba(200,75,49,.4); }}
  .country-card.charted-no {{
    opacity: .5;
  }}

  .country-header {{
    padding: 12px 16px;
    background: rgba(255,255,255,.03);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .country-name {{ font-weight: 700; font-size: .95rem; flex: 1; }}
  .rank-badge {{
    font-size: .72rem; font-weight: 700;
    padding: 3px 8px; border-radius: 4px;
  }}
  .rank-badge.rank-top  {{ background: rgba(200,75,49,.2); color: var(--top); border: 1px solid rgba(200,75,49,.3); }}
  .rank-badge.rank-mid  {{ background: rgba(232,160,32,.15); color: var(--mid); border: 1px solid rgba(232,160,32,.25); }}
  .rank-badge.rank-low  {{ background: rgba(68,136,204,.15); color: var(--low); border: 1px solid rgba(68,136,204,.25); }}
  .rank-badge.none      {{ background: rgba(255,255,255,.05); color: var(--muted); border: 1px solid var(--border); }}
  .rival-count {{ font-size: .72rem; color: var(--muted); }}

  /* ── 테이블 ── */
  .rivals-wrap {{ max-height: 300px; overflow-y: auto; }}
  .rivals-wrap::-webkit-scrollbar {{ width: 4px; }}
  .rivals-wrap::-webkit-scrollbar-track {{ background: transparent; }}
  .rivals-wrap::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

  .rivals-table {{
    width: 100%; border-collapse: collapse; font-size: .82rem;
  }}
  .rivals-table thead tr {{
    background: rgba(255,255,255,.04);
    position: sticky; top: 0; z-index: 1;
  }}
  .rivals-table th {{
    padding: 6px 10px;
    text-align: left;
    font-size: .7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .04em;
  }}
  .rivals-table td {{ padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,.04); }}
  .rivals-table tr:last-child td {{ border-bottom: none; }}
  .rivals-table tr.free-row {{ background: rgba(34,187,136,.04); }}
  .rivals-table tr.disc-row {{ background: rgba(232,160,32,.03); }}
  .rivals-table tr:hover td {{ background: rgba(255,255,255,.04); }}

  .rank-num {{ color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .game-name a {{
    color: var(--text);
    text-decoration: none;
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .game-name a:hover {{ color: var(--accent2); }}

  .badge {{
    display: inline-block;
    padding: 2px 7px; border-radius: 3px;
    font-size: .7rem; font-weight: 700; white-space: nowrap;
  }}
  .badge.free {{ background: rgba(34,187,136,.2); color: var(--free); border: 1px solid rgba(34,187,136,.25); }}
  .badge.disc {{ color: #fff; }}
  .price-orig {{ color: var(--muted); text-decoration: line-through; font-size: .78rem; margin-right: 4px; }}
  .price-final {{ color: var(--accent2); font-weight: 600; }}

  .no-rival {{ padding: 14px 16px; color: var(--muted); font-size: .82rem; }}

  /* ── 범례 ── */
  .legend {{
    display: flex; gap: 20px; flex-wrap: wrap;
    padding: 12px 0 0;
    font-size: .78rem; color: var(--muted);
  }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; }}

  footer {{
    text-align: center;
    padding: 28px;
    color: var(--muted);
    font-size: .78rem;
    border-top: 1px solid var(--border);
    margin-top: 16px;
  }}

  @media (max-width: 600px) {{
    header {{ padding: 20px 16px; }}
    .main {{ padding: 16px; }}
    .stats-bar {{ padding: 12px 16px; }}
    .grid {{ grid-template-columns: 1fr; }}
    .site-title {{ font-size: 1.8rem; }}
  }}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="site-title">🗡️ <span>붉은사막</span>&nbsp;Steam 경쟁 트래커</div>
    <div class="subtitle">각국 Top Sellers 기준 · 붉은사막보다 높은 순위의 무료/할인 게임 실시간 추적</div>
    <div class="updated">🕐 {kst_str}</div>
  </div>
</header>

<div class="stats-bar">
  <div class="stats-inner">
    <div class="stat-item">
      <span class="stat-label">순위권 국가</span>
      <span class="stat-value">{len(charted)}개국</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">전체 경쟁 게임</span>
      <span class="stat-value">{total_rivals}개</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">평균 순위</span>
      <span class="stat-value">{avg_rank}위</span>
    </div>
    <div class="stat-item">
      <span class="stat-label">최고 순위 국가</span>
      <span class="stat-value" style="font-size:1rem">{best_str}</span>
    </div>
  </div>
</div>

<div class="main">
  <div class="legend">
    <div class="legend-item"><div class="dot" style="background:var(--top)"></div> Top 10</div>
    <div class="legend-item"><div class="dot" style="background:var(--mid)"></div> 11~30위</div>
    <div class="legend-item"><div class="dot" style="background:var(--low)"></div> 31위+</div>
    <div class="legend-item"><div class="dot" style="background:var(--free)"></div> FREE TO PLAY</div>
    <div class="legend-item"><div class="dot" style="background:var(--disc)"></div> 할인 중</div>
  </div>

  <div class="grid" style="margin-top:16px">
    {cards_html}
  </div>
</div>

<footer>
  Steam Top Sellers API 기반 · Crimson Desert App ID: 1143720 · 데이터는 Steam 정책상 지연될 수 있음
</footer>

</body>
</html>"""


if __name__ == "__main__":
    data = load_data()
    if not data:
        print("❌ data/crimson_desert_rivals.json 없음. 트래커 먼저 실행하세요.")
        exit(1)

    html = generate_html(data)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"✅ 대시보드 생성: {OUTPUT_FILE}")
