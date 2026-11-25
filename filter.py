"""
filter.py — Critérios de qualidade + duração + rastreio de idioma
"""
import re
import logging
from datetime import datetime, timezone
import config

logger = logging.getLogger(__name__)

YOUTUBE_CATEGORIES = {
    "1":  "Filme & Animação",   "2":  "Automóveis",          "10": "Música",
    "15": "Animais de Estimação","17": "Esportes",            "18": "Curta-metragem",
    "19": "Viagem & Eventos",   "20": "Games",               "21": "Vídeo Blog",
    "22": "Pessoas & Blogs",    "23": "Comédia",             "24": "Entretenimento",
    "25": "Notícias & Política","26": "Profissões & Tutoriais","27": "Educação",
    "28": "Ciência & Tecnologia","29": "Organizações sem fins lucrativos",
}

LANG_LABEL = {"pt": "Português 🇧🇷", "en": "English 🇺🇸", "es": "Español 🇪🇸"}

# Mapeamento de códigos de idioma da API para nossos 3 grupos
LANG_MAP = {
    "pt": "pt", "pt-br": "pt", "pt-pt": "pt",
    "en": "en", "en-us": "en", "en-gb": "en", "en-au": "en",
    "es": "es", "es-419": "es", "es-mx": "es", "es-ar": "es", "es-co": "es",
}


def _detect_lang(stat: dict, search_lang: str) -> str:
    """Detecta o idioma real do vídeo via defaultAudioLanguage ou defaultLanguage."""
    for field in ("defaultAudioLanguage", "defaultLanguage"):
        raw = stat.get(field, "").lower().strip()
        if raw in LANG_MAP:
            return LANG_MAP[raw]
        # ex: "pt-BR" → "pt"
        prefix = raw.split("-")[0]
        if prefix in LANG_MAP:
            return LANG_MAP[prefix]
    # Fallback: idioma da busca que encontrou o vídeo
    return search_lang


def parse_duration_seconds(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "PT0S")
    if not m:
        return 0
    return int(m.group(1) or 0)*3600 + int(m.group(2) or 0)*60 + int(m.group(3) or 0)


def is_excluded(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in config.EXCLUDED_TERMS)


def is_channel_new(ch: dict) -> bool:
    s = ch.get("createdAt", "")
    if not s:
        return False
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")) >= config.CHANNEL_MIN_CREATED
    except ValueError:
        return False


def calc_views_per_day(views: int, published_at: str) -> float:
    try:
        pub  = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        days = max((config.NOW - pub).days, 1)
        days = min(days, config.VIDEO_VIRAL_WINDOW_DAYS)
        return views / days
    except Exception:
        return 0.0


def get_niche(stat: dict, search_term: str) -> str:
    cat = stat.get("categoryId", "")
    return YOUTUBE_CATEGORIES.get(cat, search_term.capitalize())


def filter_videos(raw: list[dict], video_stats: dict, channel_details: dict,
                  search_term: str, mode: str = "long", lang: str = "pt") -> list[dict]:
    qualified = []
    seen = set()

    for v in raw:
        vid = v["videoId"]
        cid = v["channelId"]
        if vid in seen:
            continue
        seen.add(vid)

        if is_excluded(f"{v['title']} {v['description']}"):
            continue

        stat = video_stats.get(vid)
        ch   = channel_details.get(cid)
        if not stat or not ch:
            continue

        # Duração
        dur = parse_duration_seconds(stat.get("duration", "PT0S"))
        if mode == "shorts" and dur > config.SHORTS_MAX_SECONDS:
            continue
        if mode == "long"   and dur < config.LONG_MIN_SECONDS:
            continue

        if not is_channel_new(ch):
            continue
        if stat["viewCount"] < config.VIDEO_MIN_VIEWS:
            continue

        vpd = calc_views_per_day(stat["viewCount"], stat["publishedAt"])
        if vpd < config.VIDEO_MIN_VIEWS_PER_DAY:
            continue

        niche = get_niche(stat, search_term)
        # Usa o idioma real do vídeo (detectado via API), não o idioma da busca
        detected_lang = _detect_lang(stat, lang)

        qualified.append({
            "videoId":        vid,
            "videoTitle":     stat["title"],
            "videoUrl":       f"https://youtube.com/watch?v={vid}",
            "thumbnailUrl":   stat["thumbnailUrl"],
            "viewCount":      stat["viewCount"],
            "likeCount":      stat["likeCount"],
            "viewsPerDay":    round(vpd, 0),
            "durationSecs":   dur,
            "publishedAt":    stat["publishedAt"],
            "channelId":      cid,
            "channelTitle":   ch["channelTitle"],
            "channelUrl":     f"https://youtube.com/channel/{cid}",
            "channelCreated": ch["createdAt"],
            "subscriberCount": ch["subscriberCount"],
            "niche":          niche,
            "searchTerm":     search_term,
            "language":       detected_lang,
            "languageLabel":  LANG_LABEL.get(detected_lang, detected_lang),
            "mode":           mode,
        })

    return qualified
