"""
reporter.py — Gera o relatório HTML com ranking por nicho
"""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
import config

NICHE_EMOJIS = {
    "Música": "🎵", "Games": "🎮", "Educação": "📚", "Ciência & Tecnologia": "💻",
    "Entretenimento": "🎬", "Comédia": "😂", "Esportes": "⚽", "Viagem & Eventos": "✈️",
    "Pessoas & Blogs": "🗣️", "Notícias & Política": "📰", "Beleza": "💄",
    "Moda": "👗", "Culinária": "🍳", "Finanças": "💰", "Fitness": "💪",
}


def _fmt_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


def _fmt_date(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso


def _channel_age_days(created_at: str) -> int:
    try:
        d = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return 0


def build_niche_ranking(videos: list[dict]) -> list[dict]:
    """Agrupa vídeos por nicho e calcula métricas de ranking."""
    niches: dict[str, dict] = defaultdict(lambda: {
        "totalViews": 0, "totalVideos": 0, "channels": set(),
        "avgViewsPerDay": 0.0, "topVideo": None,
    })

    for v in videos:
        n = v["niche"]
        niches[n]["totalViews"] += v["viewCount"]
        niches[n]["totalVideos"] += 1
        niches[n]["channels"].add(v["channelId"])
        niches[n]["avgViewsPerDay"] += v["viewsPerDay"]
        if niches[n]["topVideo"] is None or v["viewCount"] > niches[n]["topVideo"]["viewCount"]:
            niches[n]["topVideo"] = v

    ranking = []
    for niche, data in niches.items():
        videos_count = data["totalVideos"]
        ranking.append({
            "niche":         niche,
            "emoji":         NICHE_EMOJIS.get(niche, "🔥"),
            "totalViews":    data["totalViews"],
            "totalVideos":   videos_count,
            "channelCount":  len(data["channels"]),
            "avgViewsPerDay": round(data["avgViewsPerDay"] / videos_count, 0),
            "topVideo":      data["topVideo"],
        })

    return sorted(ranking, key=lambda x: x["totalViews"], reverse=True)


def generate_html(videos: list[dict], run_date: str) -> str:
    niche_ranking = build_niche_ranking(videos)
    top_channels = _top_channels(videos)

    # Build niche cards HTML
    niche_cards = ""
    for i, n in enumerate(niche_ranking, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"#{i}"
        tv = n.get("topVideo") or {}
        niche_cards += f"""
        <div class="niche-card {'top-niche' if i <= 3 else ''}">
          <div class="niche-rank">{medal}</div>
          <div class="niche-info">
            <div class="niche-name">{n['emoji']} {n['niche']}</div>
            <div class="niche-stats">
              <span class="stat-pill views">👁 {_fmt_number(n['totalViews'])} views totais</span>
              <span class="stat-pill">📹 {n['totalVideos']} vídeos virais</span>
              <span class="stat-pill">📢 {n['channelCount']} canais</span>
              <span class="stat-pill speed">⚡ {_fmt_number(int(n['avgViewsPerDay']))} views/dia (média)</span>
            </div>
            {f'<div class="top-video-hint">🏆 Top vídeo: <a href="{tv.get("videoUrl","")}" target="_blank">{tv.get("videoTitle","")[:60]}...</a></div>' if tv else ''}
          </div>
        </div>"""

    # Build video rows HTML
    video_rows = ""
    for v in sorted(videos, key=lambda x: x["viewCount"], reverse=True)[:100]:
        age = _channel_age_days(v["channelCreated"])
        video_rows += f"""
        <tr>
          <td><a href="{v['videoUrl']}" target="_blank" class="video-link">
            <img src="{v['thumbnailUrl']}" class="thumb" onerror="this.style.display='none'">
            {v['videoTitle'][:55]}{'...' if len(v['videoTitle']) > 55 else ''}
          </a></td>
          <td><a href="{v['channelUrl']}" target="_blank" class="channel-link">{v['channelTitle']}</a>
            <div class="channel-age">{age} dias de vida</div></td>
          <td class="num">{_fmt_number(v['viewCount'])}</td>
          <td class="num speed-col">⚡ {_fmt_number(int(v['viewsPerDay']))}/dia</td>
          <td><span class="niche-badge">{v['niche']}</span></td>
          <td class="num">{_fmt_number(v['subscriberCount'])}</td>
          <td>{_fmt_date(v['publishedAt'])}</td>
        </tr>"""

    # Build channel ranking
    channel_rows = ""
    for i, ch in enumerate(top_channels[:20], 1):
        age = _channel_age_days(ch["createdAt"])
        channel_rows += f"""
        <tr>
          <td class="num">{i}</td>
          <td><a href="{ch['channelUrl']}" target="_blank" class="channel-link">{ch['channelTitle']}</a>
            <div class="channel-age">{age} dias de vida</div></td>
          <td class="num">{ch['viralVideos']}</td>
          <td class="num">{_fmt_number(ch['totalViews'])}</td>
          <td><span class="niche-badge">{ch['niche']}</span></td>
          <td class="num">{_fmt_number(ch['subscriberCount'])}</td>
        </tr>"""

    total_views = sum(v["viewCount"] for v in videos)
    total_channels = len({v["channelId"] for v in videos})

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔥 Viral Finder — {run_date}</title>
<style>
  :root {{
    --bg: #0f0f13; --surface: #1a1a24; --surface2: #22222f;
    --accent: #7c3aed; --accent2: #06b6d4; --gold: #f59e0b;
    --text: #e2e8f0; --muted: #94a3b8; --border: #2d2d3f;
    --green: #10b981; --red: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; line-height: 1.6; }}
  
  /* Header */
  .header {{ background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1e3a2f 100%);
    padding: 2.5rem 2rem; text-align: center; border-bottom: 1px solid var(--border); }}
  .header h1 {{ font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(90deg, #a78bfa, #06b6d4); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; }}
  .header p {{ color: var(--muted); margin-top: 0.4rem; font-size: 0.95rem; }}
  .run-date {{ display: inline-block; margin-top: 0.8rem; padding: 0.3rem 1rem;
    background: rgba(124,58,237,0.2); border: 1px solid var(--accent); border-radius: 999px;
    font-size: 0.85rem; color: #a78bfa; }}
  
  /* Summary cards */
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem; padding: 2rem; max-width: 1200px; margin: 0 auto; }}
  .sum-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.2rem; text-align: center; }}
  .sum-card .val {{ font-size: 2rem; font-weight: 800; color: var(--accent2); }}
  .sum-card .lbl {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.2rem; }}

  /* Sections */
  .section {{ max-width: 1200px; margin: 0 auto; padding: 1rem 2rem 2rem; }}
  .section h2 {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 1.2rem;
    padding-bottom: 0.6rem; border-bottom: 2px solid var(--border);
    display: flex; align-items: center; gap: 0.5rem; }}

  /* Niche cards */
  .niche-grid {{ display: flex; flex-direction: column; gap: 0.8rem; }}
  .niche-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1rem 1.2rem; display: flex; align-items: flex-start; gap: 1rem;
    transition: border-color 0.2s; }}
  .niche-card:hover {{ border-color: var(--accent); }}
  .niche-card.top-niche {{ border-color: var(--gold); background: linear-gradient(135deg, #1a1a24, #1f1a0f); }}
  .niche-rank {{ font-size: 1.8rem; min-width: 2.5rem; text-align: center; }}
  .niche-name {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; }}
  .niche-stats {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
  .stat-pill {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 999px;
    padding: 0.2rem 0.7rem; font-size: 0.8rem; color: var(--muted); }}
  .stat-pill.views {{ color: var(--accent2); border-color: var(--accent2); }}
  .stat-pill.speed {{ color: var(--green); border-color: var(--green); }}
  .top-video-hint {{ margin-top: 0.5rem; font-size: 0.8rem; color: var(--muted); }}
  .top-video-hint a {{ color: var(--accent2); text-decoration: none; }}
  .top-video-hint a:hover {{ text-decoration: underline; }}

  /* Tables */
  .table-wrap {{ overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  th {{ background: var(--surface2); padding: 0.8rem 1rem; text-align: left;
    font-weight: 600; color: var(--muted); white-space: nowrap; }}
  td {{ padding: 0.75rem 1rem; border-top: 1px solid var(--border); vertical-align: middle; }}
  tr:hover td {{ background: rgba(124,58,237,0.05); }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }}
  .speed-col {{ color: var(--green); }}
  .thumb {{ width: 80px; height: 45px; object-fit: cover; border-radius: 4px;
    margin-right: 0.5rem; vertical-align: middle; }}
  .video-link {{ color: var(--text); text-decoration: none; display: flex;
    align-items: center; gap: 0.5rem; }}
  .video-link:hover {{ color: var(--accent2); }}
  .channel-link {{ color: var(--accent2); text-decoration: none; font-weight: 600; }}
  .channel-link:hover {{ text-decoration: underline; }}
  .channel-age {{ font-size: 0.75rem; color: var(--muted); }}
  .niche-badge {{ background: rgba(124,58,237,0.15); border: 1px solid var(--accent);
    color: #a78bfa; border-radius: 999px; padding: 0.15rem 0.6rem; font-size: 0.75rem;
    white-space: nowrap; }}

  /* Footer */
  .footer {{ text-align: center; padding: 2rem; color: var(--muted); font-size: 0.8rem;
    border-top: 1px solid var(--border); margin-top: 2rem; }}
  
  @media (max-width: 600px) {{
    .header h1 {{ font-size: 1.6rem; }}
    .section {{ padding: 1rem; }}
    .thumb {{ display: none; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🔥 Viral Finder</h1>
  <p>Canais jovens (≤ 90 dias) com vídeos que bombaram no YouTube</p>
  <div class="run-date">📅 Relatório gerado em {run_date}</div>
</div>

<!-- Summary -->
<div class="summary">
  <div class="sum-card"><div class="val">{len(videos)}</div><div class="lbl">Vídeos virais encontrados</div></div>
  <div class="sum-card"><div class="val">{total_channels}</div><div class="lbl">Canais qualificados</div></div>
  <div class="sum-card"><div class="val">{_fmt_number(total_views)}</div><div class="lbl">Views totais</div></div>
  <div class="sum-card"><div class="val">{len(niche_ranking)}</div><div class="lbl">Nichos detectados</div></div>
</div>

<!-- Niche Ranking -->
<div class="section">
  <h2>📊 Ranking por Nicho</h2>
  <div class="niche-grid">
    {niche_cards}
  </div>
</div>

<!-- Channel Ranking -->
<div class="section">
  <h2>📢 Top Canais Virais</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>#</th><th>Canal</th><th>Vídeos virais</th><th>Views totais</th><th>Nicho</th><th>Inscritos</th></tr>
      </thead>
      <tbody>{channel_rows}</tbody>
    </table>
  </div>
</div>

<!-- Video Table -->
<div class="section">
  <h2>🎬 Top 100 Vídeos Virais</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Vídeo</th><th>Canal</th><th>Views</th><th>Velocidade</th><th>Nicho</th><th>Inscritos</th><th>Publicado</th></tr>
      </thead>
      <tbody>{video_rows}</tbody>
    </table>
  </div>
</div>

<div class="footer">
  Viral Finder — Dados extraídos da YouTube Data API v3 · Critérios: canal ≤ 90 dias · vídeo ≥ 100k views · velocidade ≥ 10k views/dia
</div>
</body>
</html>"""


def _top_channels(videos: list[dict]) -> list[dict]:
    channels: dict[str, dict] = {}
    for v in videos:
        cid = v["channelId"]
        if cid not in channels:
            channels[cid] = {
                "channelTitle": v["channelTitle"],
                "channelUrl": v["channelUrl"],
                "createdAt": v["channelCreated"],
                "subscriberCount": v["subscriberCount"],
                "niche": v["niche"],
                "viralVideos": 0,
                "totalViews": 0,
            }
        channels[cid]["viralVideos"] += 1
        channels[cid]["totalViews"] += v["viewCount"]
    return sorted(channels.values(), key=lambda x: x["totalViews"], reverse=True)


def save_report(videos: list[dict]) -> str:
    """Gera e salva o relatório HTML. Retorna o caminho do arquivo."""
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    friendly_date = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")

    html = generate_html(videos, friendly_date)

    # Salva com data no nome (histórico)
    dated_path = os.path.join(config.REPORTS_DIR, f"report_{run_date}.html")
    with open(dated_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Salva como "latest" (GitHub Pages aponta aqui)
    latest_path = os.path.join(config.REPORTS_DIR, "index.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Salva JSON para análise futura
    json_path = os.path.join(config.REPORTS_DIR, f"data_{run_date}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"✅ Relatório salvo em: {dated_path}")
    return latest_path
