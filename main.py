"""
main.py — Ponto de entrada do Viral Finder
Roda dois passes: Shorts e Vídeos Longos
"""
import logging
import sys
from fetcher import get_youtube_client, search_recent_videos, get_video_stats, get_channel_details
from filter import filter_videos
from reporter import save_report, save_landing_page
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def collect_videos(youtube, mode: str) -> list[dict]:
    """Busca, filtra e retorna vídeos qualificados para o modo dado."""
    # Mapeamento de modo para parâmetro da API
    duration_param = "short" if mode == "shorts" else "long"
    label = "📱 Shorts" if mode == "shorts" else "🎬 Vídeos Longos"

    logger.info(f"\n{'='*50}")
    logger.info(f"{label} — iniciando busca")
    logger.info(f"{'='*50}")

    all_raw = []
    for term in config.SEARCH_TERMS:
        logger.info(f"  🔍 '{term}'")
        raw = search_recent_videos(youtube, term, config.SEARCH_PUBLISHED_AFTER, duration_param)
        for item in raw:
            item["_searchTerm"] = term
        all_raw.extend(raw)

    logger.info(f"  📦 Total bruto: {len(all_raw)}")

    # Deduplica
    seen = {}
    for v in all_raw:
        if v["videoId"] not in seen:
            seen[v["videoId"]] = v
    unique = list(seen.values())
    logger.info(f"  🔄 Únicos: {len(unique)}")

    # Stats dos vídeos
    video_ids = [v["videoId"] for v in unique]
    logger.info(f"  📊 Buscando stats de {len(video_ids)} vídeos...")
    video_stats = get_video_stats(youtube, video_ids)

    # Detalhes dos canais
    channel_ids = list({v["channelId"] for v in unique})
    logger.info(f"  📢 Buscando {len(channel_ids)} canais...")
    channel_details = get_channel_details(youtube, channel_ids)

    # Filtra
    qualified = []
    for v in unique:
        term = v.get("_searchTerm", "")
        result = filter_videos([v], video_stats, channel_details, term, mode=mode)
        qualified.extend(result)

    logger.info(f"  ✅ {len(qualified)} vídeos qualificados em {label}")
    return qualified


def run():
    if not config.YOUTUBE_API_KEY:
        logger.error("❌ YOUTUBE_API_KEY não definida!")
        sys.exit(1)

    logger.info("🚀 Viral Finder iniciado — 2 modos: Shorts + Vídeos Longos")

    youtube = get_youtube_client()

    # ── Passe 1: Shorts ───────────────────────────────────────────────────────
    shorts_videos = collect_videos(youtube, mode="shorts")
    shorts_path   = save_report(shorts_videos, mode="shorts")

    # ── Passe 2: Vídeos Longos ────────────────────────────────────────────────
    long_videos = collect_videos(youtube, mode="long")
    long_path   = save_report(long_videos, mode="long")

    # ── Página inicial com links para os dois ─────────────────────────────────
    save_landing_page(
        shorts_count=len(shorts_videos),
        long_count=len(long_videos),
    )

    logger.info(f"\n🎉 Concluído!")
    logger.info(f"   📱 Shorts:        {shorts_path}")
    logger.info(f"   🎬 Vídeos Longos: {long_path}")


if __name__ == "__main__":
    run()
