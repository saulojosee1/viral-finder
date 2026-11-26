"""
main.py — Viral Finder (Foco: Canais Dark Narrados ≥ 8 min · PT + EN + ES)
"""
import logging
import sys
from fetcher import (
    YouTubeAPIError,
    get_youtube_client,
    search_recent_videos,
    get_video_stats,
    get_channel_details,
)
from filter import filter_videos
from reporter import save_report
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def collect_dark_videos(youtube) -> list[dict]:
    logger.info("=" * 60)
    logger.info("🌑 Viral Finder Dark — UFOs, Mistérios, True Crime, História & Terror")
    logger.info(
        f"📋 Critérios: canal ≤ {config.CHANNEL_MAX_AGE_DAYS}d | "
        f"duração ≥ {config.VIDEO_MIN_DURATION_SECONDS // 60} min | "
        f"views ≥ {config.VIDEO_MIN_VIEWS:,} | "
        f"velocidade ≥ {config.VIDEO_MIN_VIEWS_PER_DAY:,}/dia"
    )
    logger.info("=" * 60)

    all_raw = []
    for lang, region, lang_label in config.LANGUAGES:
        terms = config.SEARCH_TERMS.get(lang, [])
        logger.info(f"\n🌍 {lang_label}")
        lang_count = 0
        for bucket in config.DURATION_BUCKETS:
            for term in terms:
                raw = search_recent_videos(
                    youtube,
                    term,
                    config.SEARCH_PUBLISHED_AFTER,
                    video_duration=bucket,
                    lang=lang,
                    region=region,
                )
                for item in raw:
                    item["_searchTerm"] = term
                all_raw.extend(raw)
                lang_count += len(raw)
        logger.info(f"   → {lang_count} resultados brutos coletados")

    # Deduplica mantendo a primeira ocorrência
    seen: dict[str, dict] = {}
    for v in all_raw:
        if v["videoId"] not in seen:
            seen[v["videoId"]] = v
    unique = list(seen.values())
    logger.info(f"\n🔄 Vídeos únicos para inspeção: {len(unique)}")

    if not unique:
        return []

    video_ids = [v["videoId"] for v in unique]
    logger.info(f"📊 Buscando estatísticas de {len(video_ids)} vídeos...")
    video_stats = get_video_stats(youtube, video_ids)

    channel_ids = list({v["channelId"] for v in unique})
    logger.info(f"📢 Buscando detalhes de {len(channel_ids)} canais...")
    channel_details = get_channel_details(youtube, channel_ids)

    qualified = []
    for v in unique:
        result = filter_videos(
            [v],
            video_stats,
            channel_details,
            search_term=v.get("_searchTerm", ""),
            lang=v.get("language", "pt"),
        )
        qualified.extend(result)

    logger.info(f"\n✅ {len(qualified)} vídeos dark qualificados!")
    return qualified


def run():
    if not config.YOUTUBE_API_KEY:
        logger.error("❌ YOUTUBE_API_KEY não definida!")
        sys.exit(1)

    total_terms = sum(len(v) for v in config.SEARCH_TERMS.values())
    est_quota = total_terms * len(config.DURATION_BUCKETS) * 100
    logger.info(f"📊 Consumo estimado de buscas: ~{est_quota} units (limite diário: 10.000)")

    try:
        youtube = get_youtube_client()
        videos = collect_dark_videos(youtube)
    except YouTubeAPIError as err:
        # Interrompe sem sobrescrever relatórios anteriores com zeros
        logger.error(f"🛑 Execução abortada para proteger relatório atual: {err}")
        sys.exit(1)

    path = save_report(videos)
    logger.info(f"🎉 Relatório salvo em: {path}")


if __name__ == "__main__":
    run()
