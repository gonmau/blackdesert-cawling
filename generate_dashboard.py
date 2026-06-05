import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("data/crimson_desert_rivals.json")
OUTPUT_FILE = Path("index.html")

def generate_dashboard():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    countries = data.get("countries", {})
    graph_html = ""
    cards_html = ""

    for cc, c in countries.items():
        rank = c.get('crimson_desert_rank')
        if rank is None: continue
        
        rivals = c.get("rivals", [])
        free_cnt = sum(1 for r in rivals if r.get("is_free"))
        disc_cnt = sum(1 for r in rivals if r.get("is_discounted"))
        
        rival_map = {r['rank']: ("#22bb88" if r.get('is_free') else "#e8a020", r['name'], r.get('rank_diff', 0)) for r in rivals}
        cells = ""
        for i in range(1, rank + 1):
            if i == rank:
                diff = c.get('rank_diff', 0)
                diff_icon = f" {'▲' if diff>0 else '▼'}{abs(diff)}" if diff != 0 else ""
                cells += f'<div title="붉은사막: {i}위{diff_icon}" style="background:#c84b31; color:white; border:1px solid #000; width:22px; height:22px; font-size:10px; text-align:center; line-height:22px; font-weight:bold;">{i}</div>'
            elif i in rival_map:
                color, name, diff = rival_map[i]
                diff_str = f" ({'+' if diff>0 else ''}{diff})" if diff != 0 else ""
                cells += f'<div title="{i}위: {name}{diff_str}" style="background:{color}; border:1px solid #000; width:22px; height:22px; font-size:10px; text-align:center; line-height:22px; color:black; cursor:help;">{i}</div>'
            else:
                cells += '<div style="background:#222; border:1px solid #111; width:22px; height:22px;"></div>'
        
        graph_html += f"""
        <div style="margin:12px 0;">
            <div style="font-size:0.9rem; margin-bottom:5px;"><strong>{c["name"]}</strong> <span style="font-size:0.75rem; color:#aaa;">(무료:{free_cnt} / 할인:{disc_cnt})</span></div>
            <div style="display:flex; flex-wrap:wrap; max-width:900px;">{cells}</div>
        </div>"""

        rows = f"""<tr style="border-bottom:2px solid #c84b31;">
            <td style="padding:4px; color:#c84b31;">#{rank} {'▲' if c.get('rank_diff',0)>0 else '▼' if c.get('rank_diff',0)<0 else ''}{abs(c.get('rank_diff',0))}</td>
            <td style="padding:4px; font-weight:bold; color:#fff;">붉은사막 (Crimson Desert)</td>
            <td style="padding:4px;"><span style="border:1px solid #c84b31; color:#c84b31; border-radius:4px; padding:1px 4px; font-size:0.7rem; white-space:nowrap;">MAIN</span></td>
        </tr>"""
        for r in rivals:
            color = "#22bb88" if r.get('is_free') else "#e8a020"
            diff = r.get('rank_diff', 0)
            diff_text = f"<span style='font-size:0.7rem; color:{'#22bb88' if diff>0 else '#c84b31'}'>{'▲' if diff>0 else '▼'}{abs(diff)}</span>" if diff != 0 else ""
            rows += f"""<tr style="border-bottom:1px solid #222;">
                <td style="padding:4px; color:#777;">#{r['rank']} {diff_text}</td>
                <td style="padding:4px; font-weight:600; color:{color};">{r['name']}</td>
                <td style="padding:4px;"><span style="border:1px solid {color}; color:{color}; border-radius:4px; padding:1px 4px; font-size:0.7rem; white-space:nowrap; display:inline-block;">{'FREE' if r.get('is_free') else '할인중'}</span></td>
            </tr>"""
        
        cards_html += f"""
        <div class="card" style="background:#111520; padding:15px; border-radius:8px; border:1px solid #222; min-width:300px;">
            <div style="font-weight:bold; margin-bottom:10px;">{c["name"]} 🔗</div>
            <table style="width:100%; border-collapse:collapse;">{rows}</table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
</head>
<body style="background:#0a0c10; color:#eee; font-family:sans-serif; padding:20px;">
    <h1 style="text-align:center;">Steam Global Rival Tracker</h1>
    <div style="text-align:center; margin-bottom:20px;">
        <button onclick="saveDashboard()" style="padding:10px 20px; background:#c84b31; color:white; border:none; cursor:pointer; border-radius:5px;">📸 대시보드 전체 캡처 저장</button>
    </div>
    <div id="capture-area" style="background:#0a0c10;">
        <div style="background:#111520; padding:20px; border-radius:8px; margin:20px auto; max-width:900px; border:1px solid #222;">
            <h3>경쟁작 순위 분포 (붉은사막: <span style="color:#c84b31;">■</span>)</h3>
            {graph_html}
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(320px, 1fr)); gap:15px;">{cards_html}</div>
    </div>
    <script>
        function saveDashboard(){{
            html2canvas(document.querySelector("#capture-area")).then(canvas => {{
                const link = document.createElement("a");
                link.download = "dashboard_{datetime.now().strftime('%Y%m%d')}.png";
                link.href = canvas.toDataURL("image/png");
                link.click();
            }});
        }}
    </script>
</body></html>"""
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ 완료: 캡처 버튼이 추가된 대시보드가 생성되었습니다.")

if __name__ == "__main__":
    generate_dashboard()