"""
main.py — Viral Finder · PT + EN + ES · Shorts e Vídeos Longos
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
    duration_param = "short" if mode == "shorts" else "long"
    label = "📱 Shorts" if mode == "shorts" else "🎬 Vídeos Longos"

    logger.info(f"\n{'='*55}")
    logger.info(f"{label} — buscando em PT + EN + ES")
    logger.info(f"{'='*55}")

    all_raw = []

    for lang, region, lang_label in config.LANGUAGES:
        terms = config.SEARCH_TERMS.get(lang, config.SEARCH_TERMS["pt"])
        logger.info(f"\n  🌍 {lang_label}")
        for term in terms:
            raw = search_recent_videos(
                youtube, term, config.SEARCH_PUBLISHED_AFTER,
                video_duration=duration_param,
                lang=lang, region=region,
            )
            for item in raw:
                item["_searchTerm"] = term
            all_raw.extend(raw)
        logger.info(f"     → {sum(1 for v in all_raw if v.get('language') == lang)} encontrados até agora")

    # Deduplicação — mantém o registro do idioma que trouxe mais views (via stats depois)
    seen: dict[str, dict] = {}
    for v in all_raw:
        if v["videoId"] not in seen:
            seen[v["videoId"]] = v
    unique = list(seen.values())
    logger.info(f"\n  🔄 Únicos após dedup: {len(unique)}")

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
        result = filter_videos(
            [v], video_stats, channel_details,
            search_term=v.get("_searchTerm", ""),
            mode=mode,
            lang=v.get("language", "pt"),
        )
        qualified.extend(result)

    logger.info(f"  ✅ {len(qualified)} vídeos qualificados")
    return qualified


def run():
    if not config.YOUTUBE_API_KEY:
        logger.error("❌ YOUTUBE_API_KEY não definida!")
        sys.exit(1)

    logger.info("🚀 Viral Finder · PT + EN + ES · Shorts + Vídeos Longos")

    youtube = get_youtube_client()

    shorts_videos = collect_videos(youtube, mode="shorts")
    save_report(shorts_videos, mode="shorts")

    long_videos = collect_videos(youtube, mode="long")
    save_report(long_videos, mode="long")

    save_landing_page(
        shorts_count=len(shorts_videos),
        long_count=len(long_videos),
    )

    logger.info("\n🎉 Concluído!")


if __name__ == "__main__":
    run()
