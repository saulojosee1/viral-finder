"""
filter.py — Critérios para canais dark (≥ 8 min, ≤ 180 dias, ≥ 30k views, ≥ 1.5k/dia)
            + filtro anti-podcast/vlog/react/gameplay + limpeza de idioma
"""
import re
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)

YOUTUBE_CATEGORIES = {
    "1":  "Filme & Animação", "2": "Automóveis", "10": "Música",
    "15": "Animais de Estimação", "17": "Esportes", "19": "Viagem & Eventos",
    "20": "Games", "22": "Pessoas & Blogs", "23": "Comédia",
    "24": "Entretenimento", "25": "Notícias & Política",
    "26": "Profissões & Tutoriais", "27": "Educação",
    "28": "Ciência & Tecnologia",
}

LANG_LABEL = {"pt": "Português 🇧🇷", "en": "English 🇺🇸", "es": "Español 🇪🇸"}

LANG_MAP = {
    "pt": "pt", "pt-br": "pt", "pt-pt": "pt",
    "en": "en", "en-us": "en", "en-gb": "en", "en-au": "en", "en-ca": "en",
    "es": "es", "es-419": "es", "es-mx": "es", "es-ar": "es", "es-co": "es", "es-es": "es",
}

# Rejeita títulos que claramente pertencem a outros idiomas (ex: indonésio, vietnamita, scripts não-latinos)
NON_TARGET_TEXT_RE = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF"
    r"\u0102\u0103\u0110\u0111\u0128\u0129\u0168\u0169\u01A0\u01A1\u01AF\u01B0\u1EA0-\u1EF9]"
)
INDONESIAN_HINT_RE = re.compile(r"\b(yang|untuk|dari|dengan|adalah|cara membuat|begini|rahasia)\b", re.I)


def detect_lang(stat: dict, search_lang: str) -> str | None:
    """Retorna 'pt', 'en', 'es' ou None se o vídeo claramente for de outro idioma."""
    for field in ("defaultAudioLanguage", "defaultLanguage"):
        raw = stat.get(field, "").lower().strip()
        if not raw:
            continue
        if raw in LANG_MAP:
            return LANG_MAP[raw]
        prefix = raw.split("-")[0]
        if prefix in LANG_MAP:
            return LANG_MAP[prefix]
        # A API informou explicitamente outro idioma (ex: id, vi, hi, ru, fr)
        return None

    title = stat.get("title", "")
    if NON_TARGET_TEXT_RE.search(title) or INDONESIAN_HINT_RE.search(title):
        return None
    return search_lang


def parse_duration_seconds(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "PT0S")
    if not m:
        return 0
    return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


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


def video_age_days(published_at: str) -> int:
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return max((config.NOW - pub).days, 1)
    except Exception:
        return 1


def calc_views_per_day(views: int, published_at: str) -> float:
    return views / video_age_days(published_at)


def classify_dark_niche(stat: dict, search_term: str) -> str:
    """Classifica o vídeo nos subnichos dark configurados; usa categoria do YT como fallback."""
    tags = " ".join(stat.get("tags", []))
    haystack = f"{stat.get('title', '')} {tags} {search_term}".lower()

    best_niche = None
    best_hits = 0
    for niche_name, keywords in config.DARK_SUBNICHES:
        hits = sum(1 for kw in keywords if kw in haystack)
        if hits > best_hits:
            best_hits = hits
            best_niche = niche_name

    if best_niche:
        return best_niche

    cat = stat.get("categoryId", "")
    return YOUTUBE_CATEGORIES.get(cat, "Mistérios & Icebergs")


def filter_videos(raw: list[dict], video_stats: dict, channel_details: dict,
                  search_term: str, lang: str = "pt") -> list[dict]:
    qualified = []
    seen = set()

    for v in raw:
        vid = v["videoId"]
        cid = v["channelId"]
        if vid in seen:
            continue
        seen.add(vid)

        stat = video_stats.get(vid)
        ch   = channel_details.get(cid)
        if not stat or not ch:
            continue

        # Exclui GTA 6 + podcasts, vlogs, reacts, gameplays, lives
        tags_text = " ".join(stat.get("tags", []))
        full_text = f"{stat['title']} {stat.get('description', '')} {tags_text} {ch['channelTitle']}"
        if is_excluded(full_text):
            continue

        # Duração >= 8 minutos
        dur = parse_duration_seconds(stat.get("duration", "PT0S"))
        if dur < config.VIDEO_MIN_DURATION_SECONDS:
            continue

        # Canal jovem (<= 180 dias)
        if not is_channel_new(ch):
            continue

        # Views mínimas (>= 30k)
        if stat["viewCount"] < config.VIDEO_MIN_VIEWS:
            continue

        # Velocidade média (>= 1.500 views/dia)
        vpd = calc_views_per_day(stat["viewCount"], stat["publishedAt"])
        if vpd < config.VIDEO_MIN_VIEWS_PER_DAY:
            continue

        # Idioma real dentro de PT / EN / ES
        detected_lang = detect_lang(stat, lang)
        if detected_lang is None:
            continue

        niche = classify_dark_niche(stat, search_term)

        qualified.append({
            "videoId":         vid,
            "videoTitle":      stat["title"],
            "videoUrl":        f"https://youtube.com/watch?v={vid}",
            "thumbnailUrl":    stat["thumbnailUrl"],
            "viewCount":       stat["viewCount"],
            "likeCount":       stat["likeCount"],
            "viewsPerDay":     round(vpd, 0),
            "durationSecs":    dur,
            "publishedAt":     stat["publishedAt"],
            "videoAgeDays":    video_age_days(stat["publishedAt"]),
            "channelId":       cid,
            "channelTitle":    ch["channelTitle"],
            "channelUrl":      f"https://youtube.com/channel/{cid}",
            "channelCreated":  ch["createdAt"],
            "subscriberCount": ch["subscriberCount"],
            "niche":           niche,
            "searchTerm":      search_term,
            "language":        detected_lang,
            "languageLabel":   LANG_LABEL.get(detected_lang, detected_lang),
        })

    return qualified
