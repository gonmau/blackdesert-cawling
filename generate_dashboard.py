import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("data/crimson_desert_rivals.json")
OUTPUT_FILE = Path("index.html")

def generate_dashboard():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    countries = data.get("countries", {})
    generated_at = data.get("generated_at", "")
    graph_html = ""
    cards_html = ""
    not_ranked_html = ""

    for cc, c in countries.items():
        rank = c.get("crimson_desert_rank")
        rivals = c.get("rivals", [])
        free_cnt = sum(1 for r in rivals if r.get("is_free"))
        disc_cnt = sum(1 for r in rivals if r.get("is_discounted"))

        # 순위권 밖 나라는 별도 섹션에 표시
        if rank is None:
            not_ranked_html += f'<span style="color:#555; font-size:0.85rem; margin:4px 6px; display:inline-block;">{c["name"]} ({cc.upper()})</span>'
            continue

        # 순위 분포 격자
        rival_map = {
            r["rank"]: (
                "#22bb88" if r.get("is_free") else "#e8a020",
                r["name"],
                r.get("rank_diff", 0),
                r.get("discount_pct", 0),
            )
            for r in rivals
        }
        cells = ""
        for i in range(1, rank + 1):
            if i == rank:
                diff = c.get("rank_diff", 0)
                diff_icon = f" {'▲' if diff>0 else '▼'}{abs(diff)}" if diff != 0 else ""
                cells += (
                    f'<div title="붉은사막: {i}위{diff_icon}" '
                    f'style="background:#c84b31;color:white;border:1px solid #000;'
                    f'width:22px;height:22px;font-size:10px;text-align:center;'
                    f'line-height:22px;font-weight:bold;">{i}</div>'
                )
            elif i in rival_map:
                color, name_g, diff, dpct = rival_map[i]
                diff_str = f" ({'+' if diff>0 else ''}{diff})" if diff != 0 else ""
                dpct_str = f" -{dpct}%" if dpct else ""
                cells += (
                    f'<div title="{i}위: {name_g}{diff_str}{dpct_str}" '
                    f'style="background:{color};border:1px solid #000;'
                    f'width:22px;height:22px;font-size:10px;text-align:center;'
                    f'line-height:22px;color:black;cursor:help;">{i}</div>'
                )
            else:
                cells += '<div style="background:#222;border:1px solid #111;width:22px;height:22px;"></div>'

        graph_html += f"""
        <div style="margin:12px 0;">
            <div style="font-size:0.9rem;margin-bottom:5px;">
                <strong>{c["name"]}</strong>
                <span style="color:#c84b31;font-weight:bold;margin-left:6px;">#{rank}</span>
                <span style="font-size:0.75rem;color:#aaa;margin-left:6px;">(무료:{free_cnt} / 할인:{disc_cnt})</span>
            </div>
            <div style="display:flex;flex-wrap:wrap;max-width:900px;">{cells}</div>
        </div>"""

        # 카드
        rows = f"""<tr style="border-bottom:2px solid #c84b31;">
            <td style="padding:4px;color:#c84b31;">
                #{rank}
                {'<span style="font-size:0.7rem;color:#22bb88"> ▲' + str(abs(c.get("rank_diff",0))) + '</span>' if c.get("rank_diff",0)>0 else
                 '<span style="font-size:0.7rem;color:#c84b31"> ▼' + str(abs(c.get("rank_diff",0))) + '</span>' if c.get("rank_diff",0)<0 else ''}
            </td>
            <td style="padding:4px;font-weight:bold;color:#fff;">붉은사막 (Crimson Desert)</td>
            <td style="padding:4px;"><span style="border:1px solid #c84b31;color:#c84b31;border-radius:4px;padding:1px 4px;font-size:0.7rem;">MAIN</span></td>
        </tr>"""

        for r in rivals:
            color = "#22bb88" if r.get("is_free") else "#e8a020"
            diff = r.get("rank_diff", 0)
            dpct = r.get("discount_pct", 0)
            label = "FREE" if r.get("is_free") else f"할인 -{dpct}%"
            diff_text = (
                f'<span style="font-size:0.7rem;color:#22bb88">▲{abs(diff)}</span>' if diff > 0
                else f'<span style="font-size:0.7rem;color:#c84b31">▼{abs(diff)}</span>' if diff < 0
                else ""
            )
            rows += f"""<tr style="border-bottom:1px solid #222;">
                <td style="padding:4px;color:#777;">#{r['rank']} {diff_text}</td>
                <td style="padding:4px;font-weight:600;color:{color};">{r['name']}</td>
                <td style="padding:4px;">
                    <span style="border:1px solid {color};color:{color};border-radius:4px;padding:1px 4px;font-size:0.7rem;white-space:nowrap;">{label}</span>
                </td>
            </tr>"""

        cards_html += f"""
        <div class="card" style="background:#111520;padding:15px;border-radius:8px;border:1px solid #222;min-width:300px;">
            <div style="font-weight:bold;margin-bottom:10px;">{c["name"]} ({cc.upper()})</div>
            <table style="width:100%;border-collapse:collapse;">{rows}</table>
        </div>"""

    # 업데이트 시각 포맷
    try:
        dt = datetime.fromisoformat(generated_at)
        time_str = dt.strftime("%Y-%m-%d %H:%M KST")
    except:
        time_str = generated_at

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>붉은사막 Steam 경쟁 트래커</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
</head>
<body style="background:#0a0c10;color:#eee;font-family:sans-serif;padding:20px;">
    <h1 style="text-align:center;">🏜️ 붉은사막 Steam 경쟁 트래커</h1>
    <div style="text-align:center;color:#666;margin-bottom:20px;font-size:0.85rem;">마지막 업데이트: {time_str}</div>
    <div style="text-align:center;margin-bottom:24px;">
        <button onclick="saveDashboard()" style="padding:10px 20px;background:#c84b31;color:white;border:none;cursor:pointer;border-radius:5px;">📸 대시보드 캡처 저장</button>
    </div>

    <div id="capture-area" style="background:#0a0c10;">
        <!-- 범례 -->
        <div style="display:flex;gap:16px;justify-content:center;margin-bottom:16px;font-size:0.8rem;">
            <span><span style="display:inline-block;width:14px;height:14px;background:#c84b31;vertical-align:middle;margin-right:4px;"></span>붉은사막</span>
            <span><span style="display:inline-block;width:14px;height:14px;background:#22bb88;vertical-align:middle;margin-right:4px;"></span>무료(F2P)</span>
            <span><span style="display:inline-block;width:14px;height:14px;background:#e8a020;vertical-align:middle;margin-right:4px;"></span>할인 중</span>
            <span><span style="display:inline-block;width:14px;height:14px;background:#222;vertical-align:middle;margin-right:4px;"></span>일반</span>
        </div>

        <!-- 순위 분포 -->
        <div style="background:#111520;padding:20px;border-radius:8px;margin:0 auto 24px;max-width:960px;border:1px solid #222;">
            <h3 style="margin-top:0;">경쟁작 순위 분포</h3>
            {graph_html}
        </div>

        <!-- 국가별 카드 -->
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:15px;max-width:960px;margin:0 auto;">
            {cards_html}
        </div>

        <!-- 순위권 밖 나라 -->
        {f'''<div style="margin:24px auto;max-width:960px;background:#111520;padding:15px;border-radius:8px;border:1px solid #222;">
            <div style="color:#555;font-size:0.8rem;margin-bottom:8px;">300위 밖 (데이터 없음)</div>
            {not_ranked_html}
        </div>''' if not_ranked_html else ''}
    </div>

    <script>
        function saveDashboard() {{
            html2canvas(document.querySelector("#capture-area")).then(canvas => {{
                const link = document.createElement("a");
                link.download = "dashboard_{datetime.now().strftime('%Y%m%d')}.png";
                link.href = canvas.toDataURL("image/png");
                link.click();
            }});
        }}
    </script>
</body>
</html>"""

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 대시보드 생성 완료")

if __name__ == "__main__":
    generate_dashboard()
