"""
filter.py — Aplica os critérios de qualidade definidos
Modos: 'shorts' (≤ 60s) | 'long' (> 20min)
"""
import re
import logging
from datetime import datetime, timezone
import config

logger = logging.getLogger(__name__)

YOUTUBE_CATEGORIES = {
    "1": "Filme & Animação", "2": "Automóveis", "10": "Música",
    "15": "Animais de Estimação", "17": "Esportes", "18": "Curta-metragem",
    "19": "Viagem & Eventos", "20": "Games", "21": "Vídeo Blog",
    "22": "Pessoas & Blogs", "23": "Comédia", "24": "Entretenimento",
    "25": "Notícias & Política", "26": "Profissões & Tutoriais",
    "27": "Educação", "28": "Ciência & Tecnologia", "29": "Organizações sem fins lucrativos",
}


def parse_duration_seconds(iso_duration: str) -> int:
    """Converte duração ISO 8601 (ex: PT1M30S) em segundos."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or "PT0S")
    if not match:
        return 0
    hours   = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def is_excluded(text: str) -> bool:
    text_lower = text.lower()
    return any(term in text_lower for term in config.EXCLUDED_TERMS)


def is_channel_new(channel_detail: dict) -> bool:
    created_at_str = channel_detail.get("createdAt", "")
    if not created_at_str:
        return False
    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        return created_at >= config.CHANNEL_MIN_CREATED
    except ValueError:
        return False


def calc_views_per_day(view_count: int, published_at: str) -> float:
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        days_alive = max((config.NOW - pub).days, 1)
        days_measured = min(days_alive, config.VIDEO_VIRAL_WINDOW_DAYS)
        return view_count / days_measured
    except Exception:
        return 0.0


def get_niche(video_stat: dict, search_term: str) -> str:
    category_id = video_stat.get("categoryId", "")
    if category_id in YOUTUBE_CATEGORIES:
        return YOUTUBE_CATEGORIES[category_id]
    return search_term.capitalize()


def filter_videos(raw_videos: list[dict], video_stats: dict, channel_details: dict,
                  search_term: str, mode: str = "long") -> list[dict]:
    """
    Filtra vídeos pelos critérios de qualidade.
    mode: 'shorts' → duração ≤ 60s | 'long' → duração > 20min
    """
    qualified = []
    seen_video_ids = set()

    for v in raw_videos:
        vid = v["videoId"]
        cid = v["channelId"]

        if vid in seen_video_ids:
            continue
        seen_video_ids.add(vid)

        full_text = f"{v['title']} {v['description']}"
        if is_excluded(full_text):
            continue

        stats   = video_stats.get(vid)
        channel = channel_details.get(cid)
        if not stats or not channel:
            continue

        # ── Critério de duração por modo ─────────────────────────────────────
        duration_secs = parse_duration_seconds(stats.get("duration", "PT0S"))
        if mode == "shorts" and duration_secs > config.SHORTS_MAX_SECONDS:
            continue
        if mode == "long" and duration_secs < config.LONG_MIN_SECONDS:
            continue

        # ── Canal novo (≤ 90 dias) ────────────────────────────────────────────
        if not is_channel_new(channel):
            continue

        # ── Views mínimas ─────────────────────────────────────────────────────
        if stats["viewCount"] < config.VIDEO_MIN_VIEWS:
            continue

        # ── Velocidade ────────────────────────────────────────────────────────
        vpd = calc_views_per_day(stats["viewCount"], stats["publishedAt"])
        if vpd < config.VIDEO_MIN_VIEWS_PER_DAY:
            continue

        niche = get_niche(stats, search_term)

        qualified.append({
            "videoId":        vid,
            "videoTitle":     stats["title"],
            "videoUrl":       f"https://youtube.com/watch?v={vid}",
            "thumbnailUrl":   stats["thumbnailUrl"],
            "viewCount":      stats["viewCount"],
            "likeCount":      stats["likeCount"],
            "viewsPerDay":    round(vpd, 0),
            "durationSecs":   duration_secs,
            "publishedAt":    stats["publishedAt"],
            "channelId":      cid,
            "channelTitle":   channel["channelTitle"],
            "channelUrl":     f"https://youtube.com/channel/{cid}",
            "channelCreated": channel["createdAt"],
            "subscriberCount": channel["subscriberCount"],
            "niche":          niche,
            "searchTerm":     search_term,
            "mode":           mode,
        })

    return qualified
