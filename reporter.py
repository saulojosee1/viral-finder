"""
reporter.py — Relatórios HTML com análise de canal dark + comparativo multilíngue
"""
import json
import os
from datetime import datetime, timezone
from collections import defaultdict
import config

NICHE_EMOJIS = {
    "Música": "🎵", "Games": "🎮", "Educação": "📚", "Ciência & Tecnologia": "💻",
    "Entretenimento": "🎬", "Comédia": "😂", "Esportes": "⚽", "Viagem & Eventos": "✈️",
    "Pessoas & Blogs": "🗣️", "Notícias & Política": "📰", "Filme & Animação": "🎥",
    "Automóveis": "🚗", "Animais de Estimação": "🐾", "Profissões & Tutoriais": "🛠️",
    "Finanças": "💰", "Culinária": "🍳",
}

MODE_META = {
    "shorts": {
        "emoji": "📱", "label": "Shorts Virais",
        "desc":  "Vídeos verticais ≤ 60 segundos",
        "accent": "#f43f5e", "accent2": "#fb7185",
        "gradient": "linear-gradient(135deg,#4c0519 0%,#0f172a 50%,#1e1b4b 100%)",
        "file": "shorts.html",
    },
    "long": {
        "emoji": "🎬", "label": "Vídeos Longos Virais",
        "desc":  "Horizontais com mais de 20 minutos",
        "accent": "#7c3aed", "accent2": "#06b6d4",
        "gradient": "linear-gradient(135deg,#1e1b4b 0%,#0f172a 50%,#1e3a2f 100%)",
        "file": "long.html",
    },
}

LANG_FLAG = {"pt": "🇧🇷", "en": "🇺🇸", "es": "🇪🇸", "": "🌐"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)

def _fmt_dur(s: int) -> str:
    if s < 60: return f"{s}s"
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"

def _fmt_date(iso: str) -> str:
    try: return datetime.fromisoformat(iso.replace("Z","+00:00")).strftime("%d/%m/%Y")
    except: return iso

def _age(iso: str) -> int:
    try: return (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z","+00:00"))).days
    except: return 0


# ── Análise por nicho ─────────────────────────────────────────────────────────

def _niche_stats(videos: list[dict]) -> list[dict]:
    """Agrega por nicho com breakdown por idioma."""
    data: dict[str, dict] = defaultdict(lambda: {
        "totalViews": 0, "totalVideos": 0, "channels": set(),
        "totalVPD": 0.0, "topVideo": None,
        "byLang": defaultdict(lambda: {"views": 0, "videos": 0}),
    })
    for v in videos:
        n = v["niche"]
        l = v.get("language", "pt")
        data[n]["totalViews"]  += v["viewCount"]
        data[n]["totalVideos"] += 1
        data[n]["channels"].add(v["channelId"])
        data[n]["totalVPD"]    += v["viewsPerDay"]
        data[n]["byLang"][l]["views"]  += v["viewCount"]
        data[n]["byLang"][l]["videos"] += 1
        if data[n]["topVideo"] is None or v["viewCount"] > data[n]["topVideo"]["viewCount"]:
            data[n]["topVideo"] = v

    result = []
    for niche, d in data.items():
        cnt      = d["totalVideos"]
        ch_count = len(d["channels"])
        avg_vpd  = d["totalVPD"] / cnt

        # ── Dark Opportunity Score (0–100) ────────────────────────────────
        compat   = config.DARK_CHANNEL_COMPAT.get(niche, 50)
        # demanda: views totais normalizados (100M = 100 pts)
        demand   = min(d["totalViews"] / 1_000_000, 100)
        # concorrência inversa: menos canais = melhor (<=2 canais = 100pts)
        comp_inv = max(0, 100 - (ch_count - 1) * 10)
        # velocidade: avg views/dia normalizados (50k/dia = 100pts)
        speed    = min(avg_vpd / 500, 100)
        opp_score = round(compat * 0.40 + demand * 0.25 + comp_inv * 0.20 + speed * 0.15)

        result.append({
            "niche":        niche,
            "emoji":        NICHE_EMOJIS.get(niche, "🔥"),
            "totalViews":   d["totalViews"],
            "totalVideos":  cnt,
            "channelCount": ch_count,
            "avgVPD":       round(avg_vpd, 0),
            "byLang":       dict(d["byLang"]),
            "topVideo":     d["topVideo"],
            "oppScore":     opp_score,
            "darkCompat":   compat,
            "darkFormat":   config.DARK_CHANNEL_FORMAT.get(niche, "Narração IA + imagens"),
        })

    return sorted(result, key=lambda x: x["totalViews"], reverse=True)


def _top_channels(videos: list[dict]) -> list[dict]:
    chs: dict[str, dict] = {}
    for v in videos:
        cid = v["channelId"]
        if cid not in chs:
            chs[cid] = {
                "channelTitle": v["channelTitle"], "channelUrl": v["channelUrl"],
                "createdAt": v["channelCreated"], "subscriberCount": v["subscriberCount"],
                "niche": v["niche"], "viralVideos": 0, "totalViews": 0,
                "languages": set(),
            }
        chs[cid]["viralVideos"] += 1
        chs[cid]["totalViews"]  += v["viewCount"]
        chs[cid]["languages"].add(v.get("language","pt"))
    return sorted(chs.values(), key=lambda x: x["totalViews"], reverse=True)


def _lang_breakdown(videos: list[dict]) -> dict:
    bd: dict[str, dict] = defaultdict(lambda: {"views": 0, "videos": 0, "channels": set()})
    for v in videos:
        l = v.get("language", "pt")
        bd[l]["views"]   += v["viewCount"]
        bd[l]["videos"]  += 1
        bd[l]["channels"].add(v["channelId"])
    return {k: {**v, "channels": len(v["channels"])} for k, v in bd.items()}


# ── CSS ───────────────────────────────────────────────────────────────────────

def _css(a: str, a2: str) -> str:
    return f"""
  :root{{--bg:#0f0f13;--surface:#1a1a24;--surface2:#22222f;--accent:{a};--accent2:{a2};
    --gold:#f59e0b;--text:#e2e8f0;--muted:#94a3b8;--border:#2d2d3f;--green:#10b981;
    --opp-high:#10b981;--opp-mid:#f59e0b;--opp-low:#ef4444;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;line-height:1.6;}}
  .header{{background:{_esc_brace("placeholder")};padding:2.5rem 2rem;text-align:center;border-bottom:1px solid var(--border);}}
  .header h1{{font-size:2.2rem;font-weight:800;background:linear-gradient(90deg,{a},{a2});
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;}}
  .header p{{color:var(--muted);margin-top:.4rem;}}
  .run-date{{display:inline-block;margin-top:.8rem;padding:.3rem 1rem;
    background:rgba(0,0,0,.3);border:1px solid var(--accent);border-radius:999px;font-size:.85rem;color:{a2};}}
  .back-link{{display:inline-block;margin-top:.8rem;margin-left:.5rem;padding:.3rem 1rem;
    background:rgba(255,255,255,.05);border:1px solid var(--border);border-radius:999px;
    font-size:.85rem;color:var(--muted);text-decoration:none;}}
  .back-link:hover{{color:var(--text);}}
  .summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));
    gap:1rem;padding:2rem;max-width:1300px;margin:0 auto;}}
  .sum-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;
    padding:1.2rem;text-align:center;}}
  .sum-card .val{{font-size:1.9rem;font-weight:800;color:var(--accent2);}}
  .sum-card .lbl{{font-size:.78rem;color:var(--muted);margin-top:.2rem;}}
  .section{{max-width:1300px;margin:0 auto;padding:1rem 2rem 2rem;}}
  .section h2{{font-size:1.25rem;font-weight:700;margin-bottom:1.2rem;padding-bottom:.6rem;
    border-bottom:2px solid var(--border);}}

  /* Lang breakdown */
  .lang-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:2rem;}}
  .lang-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.2rem;}}
  .lang-title{{font-size:1.1rem;font-weight:700;margin-bottom:.8rem;}}
  .lang-stat{{display:flex;justify-content:space-between;padding:.3rem 0;border-bottom:1px solid var(--border);font-size:.85rem;}}
  .lang-stat:last-child{{border-bottom:none;}}
  .lang-val{{font-weight:700;color:var(--accent2);}}

  /* Opportunity cards */
  .opp-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem;}}
  .opp-card{{background:var(--surface);border-radius:14px;padding:1.4rem;position:relative;overflow:hidden;}}
  .opp-card.high{{border:2px solid var(--opp-high);}}
  .opp-card.mid {{border:2px solid var(--opp-mid);}}
  .opp-card.low {{border:2px solid var(--opp-low);}}
  .opp-score-badge{{position:absolute;top:1rem;right:1rem;width:52px;height:52px;
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:1.1rem;font-weight:900;}}
  .high .opp-score-badge{{background:rgba(16,185,129,.15);color:var(--opp-high);border:2px solid var(--opp-high);}}
  .mid  .opp-score-badge{{background:rgba(245,158,11,.15);color:var(--opp-mid); border:2px solid var(--opp-mid);}}
  .low  .opp-score-badge{{background:rgba(239,68,68,.15); color:var(--opp-low); border:2px solid var(--opp-low);}}
  .opp-niche{{font-size:1.1rem;font-weight:800;margin-bottom:.3rem;}}
  .opp-label{{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.72rem;
    font-weight:700;margin-bottom:.8rem;}}
  .high .opp-label{{background:rgba(16,185,129,.15);color:var(--opp-high);}}
  .mid  .opp-label{{background:rgba(245,158,11,.15); color:var(--opp-mid);}}
  .low  .opp-label{{background:rgba(239,68,68,.15);  color:var(--opp-low);}}
  .opp-row{{display:flex;justify-content:space-between;font-size:.82rem;padding:.25rem 0;
    border-bottom:1px solid var(--border);}}
  .opp-row:last-child{{border:none;}}
  .opp-key{{color:var(--muted);}}
  .opp-val{{font-weight:600;}}
  .opp-format{{margin-top:.8rem;font-size:.8rem;color:var(--muted);
    background:var(--surface2);padding:.5rem .8rem;border-radius:8px;}}
  .opp-lang-bar{{margin-top:.8rem;}}
  .opp-lang-row{{display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem;font-size:.78rem;}}
  .opp-bar-bg{{flex:1;background:var(--surface2);border-radius:999px;height:6px;overflow:hidden;}}
  .opp-bar-fill{{height:100%;border-radius:999px;background:var(--accent2);}}

  /* Niche table */
  .niche-grid{{display:flex;flex-direction:column;gap:.7rem;}}
  .niche-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;
    padding:1rem 1.2rem;display:flex;align-items:flex-start;gap:1rem;transition:border-color .2s;}}
  .niche-card:hover{{border-color:var(--accent);}}
  .niche-card.top{{border-color:var(--gold);background:linear-gradient(135deg,#1a1a24,#1f1a0f);}}
  .niche-rank{{font-size:1.7rem;min-width:2.4rem;text-align:center;}}
  .niche-name{{font-size:1rem;font-weight:700;margin-bottom:.4rem;}}
  .niche-stats{{display:flex;flex-wrap:wrap;gap:.35rem;}}
  .pill{{background:var(--surface2);border:1px solid var(--border);border-radius:999px;
    padding:.18rem .6rem;font-size:.78rem;color:var(--muted);}}
  .pill.v{{color:var(--accent2);border-color:var(--accent2);}}
  .pill.s{{color:var(--green);border-color:var(--green);}}
  .lang-pills{{display:flex;gap:.3rem;margin-top:.4rem;flex-wrap:wrap;}}
  .lang-pill{{border-radius:999px;padding:.15rem .5rem;font-size:.72rem;font-weight:600;
    background:rgba(255,255,255,.07);}}
  .top-hint{{margin-top:.4rem;font-size:.78rem;color:var(--muted);}}
  .top-hint a{{color:var(--accent2);text-decoration:none;}}

  /* Tables */
  .table-wrap{{overflow-x:auto;border-radius:12px;border:1px solid var(--border);}}
  table{{width:100%;border-collapse:collapse;font-size:.86rem;}}
  th{{background:var(--surface2);padding:.75rem 1rem;text-align:left;font-weight:600;color:var(--muted);white-space:nowrap;}}
  td{{padding:.7rem 1rem;border-top:1px solid var(--border);vertical-align:middle;}}
  tr:hover td{{background:rgba(124,58,237,.05);}}
  .num{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;}}
  .spd{{color:var(--green);}}
  .rk{{text-align:center;font-weight:800;color:var(--accent2);font-size:1.05rem;}}
  .thumb{{width:78px;height:44px;object-fit:cover;border-radius:4px;margin-right:.5rem;vertical-align:middle;}}
  .vlink{{color:var(--text);text-decoration:none;display:flex;align-items:center;gap:.4rem;}}
  .vlink:hover{{color:var(--accent2);}}
  .clink{{color:var(--accent2);text-decoration:none;font-weight:600;}}
  .clink:hover{{text-decoration:underline;}}
  .cage{{font-size:.73rem;color:var(--muted);}}
  .nbadge{{background:rgba(124,58,237,.15);border:1px solid var(--accent);
    color:{a2};border-radius:999px;padding:.13rem .55rem;font-size:.73rem;white-space:nowrap;}}
  .lbadge{{border-radius:999px;padding:.13rem .55rem;font-size:.73rem;white-space:nowrap;
    background:rgba(255,255,255,.07);}}
  .footer{{text-align:center;padding:2rem;color:var(--muted);font-size:.78rem;
    border-top:1px solid var(--border);margin-top:2rem;}}
  @media(max-width:600px){{.header h1{{font-size:1.5rem;}}.section{{padding:1rem;}}.thumb{{display:none;}}}}
"""

def _esc_brace(s): return s  # dummy — used only to avoid f-string issues below


def generate_html(videos: list[dict], mode: str, run_date: str) -> str:
    meta         = MODE_META[mode]
    niche_data   = _niche_stats(videos)
    top_channels = _top_channels(videos)
    lang_bd      = _lang_breakdown(videos)
    total_views  = sum(v["viewCount"] for v in videos)
    total_ch     = len({v["channelId"] for v in videos})

    # ── Language breakdown cards ──────────────────────────────────────────────
    lang_cards = ""
    for lang, region, lbl in config.LANGUAGES:
        d = lang_bd.get(lang, {"views": 0, "videos": 0, "channels": 0})
        pct = round(d["views"] / total_views * 100) if total_views else 0
        lang_cards += f"""
        <div class="lang-card">
          <div class="lang-title">{lbl}</div>
          <div class="lang-stat"><span>Views totais</span><span class="lang-val">{_fmt(d['views'])}</span></div>
          <div class="lang-stat"><span>Vídeos virais</span><span class="lang-val">{d['videos']}</span></div>
          <div class="lang-stat"><span>Canais únicos</span><span class="lang-val">{d['channels']}</span></div>
          <div class="lang-stat"><span>% das views totais</span><span class="lang-val">{pct}%</span></div>
        </div>"""

    # ── Dark opportunity cards (top 6 por oppScore) ───────────────────────────
    top_opp = sorted(niche_data, key=lambda x: x["oppScore"], reverse=True)[:6]
    opp_cards = ""
    for n in top_opp:
        cls   = "high" if n["oppScore"] >= 70 else ("mid" if n["oppScore"] >= 45 else "low")
        label = "🟢 ALTA OPORTUNIDADE" if cls == "high" else ("🟡 OPORTUNIDADE MÉDIA" if cls == "mid" else "🔴 BAIXA OPORTUNIDADE")
        # lang bars
        max_lv = max((n["byLang"].get(l, {}).get("views", 0) for l in ["pt","en","es"]), default=1) or 1
        lang_bars = ""
        for lang, _, lbl in config.LANGUAGES:
            lv = n["byLang"].get(lang, {}).get("views", 0)
            pct = round(lv / max_lv * 100) if max_lv else 0
            lang_bars += f"""
            <div class="opp-lang-row">
              <span style="width:90px">{LANG_FLAG.get(lang,"")} {lbl.split()[0]}</span>
              <div class="opp-bar-bg"><div class="opp-bar-fill" style="width:{pct}%"></div></div>
              <span style="width:50px;text-align:right">{_fmt(lv)}</span>
            </div>"""
        tv = n.get("topVideo") or {}
        opp_cards += f"""
        <div class="opp-card {cls}">
          <div class="opp-score-badge">{n['oppScore']}</div>
          <div class="opp-niche">{n['emoji']} {n['niche']}</div>
          <span class="opp-label">{label}</span>
          <div class="opp-row"><span class="opp-key">👁 Views totais</span><span class="opp-val">{_fmt(n['totalViews'])}</span></div>
          <div class="opp-row"><span class="opp-key">📹 Vídeos virais</span><span class="opp-val">{n['totalVideos']}</span></div>
          <div class="opp-row"><span class="opp-key">📢 Canais concorrentes</span><span class="opp-val">{n['channelCount']}</span></div>
          <div class="opp-row"><span class="opp-key">⚡ Velocidade média</span><span class="opp-val">{_fmt(int(n['avgVPD']))}/dia</span></div>
          <div class="opp-row"><span class="opp-key">🤖 Compat. dark channel</span><span class="opp-val">{n['darkCompat']}/100</span></div>
          <div class="opp-format">🎬 Formato sugerido: {n['darkFormat']}</div>
          {f'<div class="opp-format" style="margin-top:.4rem">🏆 Top vídeo: <a href="{tv.get("videoUrl","")}" target="_blank" style="color:var(--accent2)">{tv.get("videoTitle","")[:45]}…</a></div>' if tv else ''}
          <div class="opp-lang-bar">{lang_bars}</div>
        </div>"""

    # ── Niche ranking cards ───────────────────────────────────────────────────
    niche_cards = ""
    for i, n in enumerate(niche_data, 1):
        medal = ["🥇","🥈","🥉"][i-1] if i <= 3 else f"#{i}"
        tv    = n.get("topVideo") or {}
        lang_pills_html = "".join(
            f'<span class="lang-pill">{LANG_FLAG.get(l,"")} {_fmt(n["byLang"][l]["views"])} views</span>'
            for l in ["pt","en","es"] if n["byLang"].get(l, {}).get("views", 0) > 0
        )
        niche_cards += f"""
        <div class="niche-card {'top' if i<=3 else ''}">
          <div class="niche-rank">{medal}</div>
          <div class="niche-info">
            <div class="niche-name">{n['emoji']} {n['niche']} <small style="color:var(--muted);font-weight:400;font-size:.75rem">— opp. {n['oppScore']}/100</small></div>
            <div class="niche-stats">
              <span class="pill v">👁 {_fmt(n['totalViews'])}</span>
              <span class="pill">📹 {n['totalVideos']} vídeos</span>
              <span class="pill">📢 {n['channelCount']} canais</span>
              <span class="pill s">⚡ {_fmt(int(n['avgVPD']))}/dia</span>
            </div>
            <div class="lang-pills">{lang_pills_html}</div>
            {f'<div class="top-hint">🏆 <a href="{tv.get("videoUrl","")}" target="_blank">{tv.get("videoTitle","")[:60]}…</a></div>' if tv else ''}
          </div>
        </div>"""

    # ── Channel rows ──────────────────────────────────────────────────────────
    ch_rows = ""
    for i, ch in enumerate(top_channels[:20], 1):
        age   = _age(ch["createdAt"])
        langs = " ".join(LANG_FLAG.get(l,"") for l in ch.get("languages", set()))
        ch_rows += f"""
        <tr>
          <td class="rk">{i}</td>
          <td><a href="{ch['channelUrl']}" target="_blank" class="clink">{ch['channelTitle']}</a>
            <div class="cage">{age} dias de vida · {langs}</div></td>
          <td class="num">{ch['viralVideos']}</td>
          <td class="num">{_fmt(ch['totalViews'])}</td>
          <td><span class="nbadge">{ch['niche']}</span></td>
          <td class="num">{_fmt(ch['subscriberCount'])}</td>
        </tr>"""

    # ── Video rows ────────────────────────────────────────────────────────────
    vid_rows = ""
    for i, v in enumerate(sorted(videos, key=lambda x: x["viewCount"], reverse=True)[:100], 1):
        age = _age(v["channelCreated"])
        dur = _fmt_dur(v.get("durationSecs", 0))
        flag = LANG_FLAG.get(v.get("language",""), "🌐")
        vid_rows += f"""
        <tr>
          <td class="rk">{i}</td>
          <td><a href="{v['videoUrl']}" target="_blank" class="vlink">
            <img src="{v['thumbnailUrl']}" class="thumb" onerror="this.style.display='none'">
            {v['videoTitle'][:52]}{'…' if len(v['videoTitle'])>52 else ''}
          </a></td>
          <td><a href="{v['channelUrl']}" target="_blank" class="clink">{v['channelTitle']}</a>
            <div class="cage">{age} dias · {flag}</div></td>
          <td class="num">{_fmt(v['viewCount'])}</td>
          <td class="num spd">⚡ {_fmt(int(v['viewsPerDay']))}/dia</td>
          <td class="num">{dur}</td>
          <td><span class="nbadge">{v['niche']}</span></td>
          <td>{_fmt_date(v['publishedAt'])}</td>
        </tr>"""

    grad = meta["gradient"]
    a    = meta["accent"]
    a2   = meta["accent2"]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{meta['emoji']} {meta['label']} — {run_date}</title>
<style>
  .header{{background:{grad};}}
  {_css(a, a2)}
</style>
</head>
<body>
<div class="header">
  <h1>{meta['emoji']} {meta['label']}</h1>
  <p>{meta['desc']} · canais ≤ 90 dias · ≥ 100k views · ≥ 10k views/dia · 🌍 PT + EN + ES</p>
  <div class="run-date">📅 {run_date}</div>
  <a href="index.html" class="back-link">← Início</a>
</div>

<div class="summary">
  <div class="sum-card"><div class="val">{len(videos)}</div><div class="lbl">Vídeos virais</div></div>
  <div class="sum-card"><div class="val">{total_ch}</div><div class="lbl">Canais qualificados</div></div>
  <div class="sum-card"><div class="val">{_fmt(total_views)}</div><div class="lbl">Views totais</div></div>
  <div class="sum-card"><div class="val">{len(niche_data)}</div><div class="lbl">Nichos detectados</div></div>
  <div class="sum-card"><div class="val">3</div><div class="lbl">Idiomas monitorados</div></div>
</div>

<div class="section">
  <h2>🌍 Comparativo por Idioma</h2>
  <div class="lang-grid">{lang_cards}</div>
</div>

<div class="section">
  <h2>🎯 Oportunidades para Canal Dark — Top Nichos</h2>
  <p style="color:var(--muted);font-size:.85rem;margin-bottom:1.2rem">
    Score considera: compatibilidade dark (40%) · demanda/views (25%) · baixa concorrência (20%) · velocidade (15%)
  </p>
  <div class="opp-grid">{opp_cards}</div>
</div>

<div class="section">
  <h2>📊 Ranking por Nicho</h2>
  <div class="niche-grid">{niche_cards}</div>
</div>

<div class="section">
  <h2>📢 Top 20 Canais</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>#</th><th>Canal</th><th>Vídeos virais</th><th>Views totais</th><th>Nicho</th><th>Inscritos</th></tr></thead>
      <tbody>{ch_rows}</tbody>
    </table>
  </div>
</div>

<div class="section">
  <h2>🎬 Top 100 Vídeos</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>#</th><th>Vídeo</th><th>Canal</th><th>Views</th><th>Velocidade</th><th>Duração</th><th>Nicho</th><th>Publicado</th></tr></thead>
      <tbody>{vid_rows}</tbody>
    </table>
  </div>
</div>

<div class="footer">
  Viral Finder · YouTube Data API v3 · Canal ≤ 90 dias · ≥ 100k views · ≥ 10k views/dia · GTA 6 excluído · PT + EN + ES
</div>
</body>
</html>"""


def save_report(videos: list[dict], mode: str) -> str:
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    run_ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    friendly = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")
    meta     = MODE_META[mode]

    html = generate_html(videos, mode, friendly)

    for path in [
        os.path.join(config.REPORTS_DIR, f"{mode}_{run_ts}.html"),
        os.path.join(config.REPORTS_DIR, meta["file"]),
    ]:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    with open(os.path.join(config.REPORTS_DIR, f"{mode}_{run_ts}.json"), "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"✅ Relatório {mode} salvo")
    return os.path.join(config.REPORTS_DIR, meta["file"])


def save_landing_page(shorts_count: int, long_count: int):
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    friendly = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🔥 Viral Finder</title>
<style>
  :root{{--bg:#0f0f13;--surface:#1a1a24;--border:#2d2d3f;--text:#e2e8f0;--muted:#94a3b8;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
    min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:2rem;}}
  h1{{font-size:2.5rem;font-weight:900;background:linear-gradient(90deg,#a78bfa,#06b6d4);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.4rem;}}
  .sub{{color:var(--muted);font-size:.9rem;margin-bottom:.3rem;}}
  .run{{color:var(--muted);font-size:.78rem;margin-bottom:3rem;}}
  .cards{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;width:100%;max-width:700px;}}
  .card{{background:var(--surface);border:2px solid var(--border);border-radius:20px;
    padding:2.5rem 2rem;text-align:center;text-decoration:none;color:var(--text);transition:transform .2s,border-color .2s;}}
  .card:hover{{transform:translateY(-4px);}}
  .card.s{{border-color:#f43f5e;}}.card.s:hover{{box-shadow:0 8px 32px rgba(244,63,94,.2);}}
  .card.l{{border-color:#7c3aed;}}.card.l:hover{{box-shadow:0 8px 32px rgba(124,58,237,.2);}}
  .ic{{font-size:3rem;margin-bottom:1rem;}}
  .ct{{font-size:1.3rem;font-weight:800;margin-bottom:.4rem;}}
  .cd{{font-size:.82rem;color:var(--muted);margin-bottom:.6rem;}}
  .flags{{font-size:1.1rem;margin-bottom:.8rem;}}
  .cv{{font-size:2rem;font-weight:900;}}
  .card.s .cv{{color:#fb7185;}}.card.l .cv{{color:#a78bfa;}}
  .cl{{font-size:.78rem;color:var(--muted);}}
  .footer{{margin-top:3rem;color:var(--muted);font-size:.75rem;text-align:center;}}
  @media(max-width:500px){{.cards{{grid-template-columns:1fr;}}h1{{font-size:1.8rem;}}}}
</style>
</head>
<body>
  <h1>🔥 Viral Finder</h1>
  <p class="sub">Canais novos (≤ 90 dias) com vídeos que bombaram no YouTube</p>
  <p class="sub">🌍 Monitorando: 🇧🇷 Português · 🇺🇸 English · 🇪🇸 Español</p>
  <p class="run">Última atualização: {friendly}</p>
  <div class="cards">
    <a href="shorts.html" class="card s">
      <div class="ic">📱</div>
      <div class="ct">Shorts Virais</div>
      <div class="cd">Vídeos verticais ≤ 60 segundos</div>
      <div class="flags">🇧🇷 🇺🇸 🇪🇸</div>
      <div class="cv">{shorts_count}</div>
      <div class="cl">vídeos qualificados</div>
    </a>
    <a href="long.html" class="card l">
      <div class="ic">🎬</div>
      <div class="ct">Vídeos Longos Virais</div>
      <div class="cd">Horizontais com mais de 20 minutos</div>
      <div class="flags">🇧🇷 🇺🇸 🇪🇸</div>
      <div class="cv">{long_count}</div>
      <div class="cl">vídeos qualificados</div>
    </a>
  </div>
  <div class="footer">
    Critérios: canal ≤ 90 dias · ≥ 100k views · ≥ 10k views/dia (14 dias) · GTA 6 excluído<br>
    Atualizado automaticamente toda terça e sexta-feira
  </div>
</body>
</html>"""
    with open(os.path.join(config.REPORTS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Landing page salva")
