"""
filter.py — Aplica os critérios de qualidade definidos
"""
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


def is_excluded(text: str) -> bool:
    """Retorna True se o texto contém termos excluídos (ex: GTA 6)."""
    text_lower = text.lower()
    return any(term in text_lower for term in config.EXCLUDED_TERMS)


def is_channel_new(channel_detail: dict) -> bool:
    """Verifica se o canal foi criado dentro da janela de 90 dias."""
    created_at_str = channel_detail.get("createdAt", "")
    if not created_at_str:
        return False
    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        return created_at >= config.CHANNEL_MIN_CREATED
    except ValueError:
        return False


def calc_views_per_day(view_count: int, published_at: str) -> float:
    """Calcula a média de views por dia desde a publicação."""
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        days_alive = max((config.NOW - pub).days, 1)
        # Limita ao teto da janela de viralização
        days_measured = min(days_alive, config.VIDEO_VIRAL_WINDOW_DAYS)
        return view_count / days_measured
    except Exception:
        return 0.0


def get_niche(video_stat: dict, search_term: str) -> str:
    """Determina o nicho do vídeo via categoria do YouTube ou termo de busca."""
    category_id = video_stat.get("categoryId", "")
    if category_id in YOUTUBE_CATEGORIES:
        return YOUTUBE_CATEGORIES[category_id]
    # Fallback: usa o termo de busca capitalizado
    return search_term.capitalize()


def filter_videos(raw_videos: list[dict], video_stats: dict, channel_details: dict, search_term: str) -> list[dict]:
    """
    Recebe os vídeos brutos e retorna apenas os que passam em todos os critérios.
    """
    qualified = []
    seen_video_ids = set()

    for v in raw_videos:
        vid = v["videoId"]
        cid = v["channelId"]

        if vid in seen_video_ids:
            continue
        seen_video_ids.add(vid)

        # Verificar exclusões no título/descrição
        full_text = f"{v['title']} {v['description']}"
        if is_excluded(full_text):
            logger.debug(f"Excluído por termo bloqueado: {v['title']}")
            continue

        stats = video_stats.get(vid)
        channel = channel_details.get(cid)

        if not stats or not channel:
            continue

        # Critério 1: canal novo (≤ 90 dias)
        if not is_channel_new(channel):
            continue

        # Critério 2: vídeo com ≥ 100k views
        if stats["viewCount"] < config.VIDEO_MIN_VIEWS:
            continue

        # Critério 3: velocidade ≥ 10k views/dia na janela de 14 dias
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
            "publishedAt":    stats["publishedAt"],
            "channelId":      cid,
            "channelTitle":   channel["channelTitle"],
            "channelUrl":     f"https://youtube.com/channel/{cid}",
            "channelCreated": channel["createdAt"],
            "subscriberCount": channel["subscriberCount"],
            "niche":          niche,
            "searchTerm":     search_term,
        })

    return qualified
