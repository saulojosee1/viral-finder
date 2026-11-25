"""
main.py — Ponto de entrada do Viral Finder
"""
import logging
import sys
from fetcher import get_youtube_client, search_recent_videos, get_video_stats, get_channel_details
from filter import filter_videos
from reporter import save_report
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run():
    if not config.YOUTUBE_API_KEY:
        logger.error("❌ YOUTUBE_API_KEY não definida! Configure a variável de ambiente.")
        sys.exit(1)

    logger.info("🚀 Viral Finder iniciado")
    logger.info(f"📋 Critérios: canal ≤ {config.CHANNEL_MAX_AGE_DAYS} dias | vídeo ≥ {config.VIDEO_MIN_VIEWS:,} views | velocidade ≥ {config.VIDEO_MIN_VIEWS_PER_DAY:,} views/dia")

    youtube = get_youtube_client()
    all_raw_videos = []

    # 1. Buscar vídeos por todos os termos de pesquisa
    for term in config.SEARCH_TERMS:
        logger.info(f"🔍 Buscando: '{term}'")
        raw = search_recent_videos(youtube, term, config.SEARCH_PUBLISHED_AFTER)
        for item in raw:
            item["_searchTerm"] = term  # guarda o termo para classificação de nicho
        all_raw_videos.extend(raw)
        logger.info(f"   → {len(raw)} vídeos encontrados")

    logger.info(f"\n📦 Total bruto: {len(all_raw_videos)} vídeos (antes dos filtros)")

    # 2. Deduplica por videoId (mesmo vídeo pode aparecer em termos diferentes)
    seen = {}
    for v in all_raw_videos:
        vid = v["videoId"]
        if vid not in seen:
            seen[vid] = v
    unique_videos = list(seen.values())
    logger.info(f"🔄 Após deduplicação: {len(unique_videos)} vídeos únicos")

    # 3. Busca estatísticas detalhadas dos vídeos (em lotes de 50)
    video_ids = [v["videoId"] for v in unique_videos]
    logger.info(f"📊 Buscando estatísticas de {len(video_ids)} vídeos...")
    video_stats = get_video_stats(youtube, video_ids)

    # 4. Busca detalhes dos canais (em lotes de 50)
    channel_ids = list({v["channelId"] for v in unique_videos})
    logger.info(f"📢 Buscando detalhes de {len(channel_ids)} canais...")
    channel_details = get_channel_details(youtube, channel_ids)

    # 5. Aplica os filtros de qualidade
    logger.info("🔎 Aplicando critérios de qualidade...")
    qualified = []
    for v in unique_videos:
        term = v.get("_searchTerm", "")
        result = filter_videos([v], video_stats, channel_details, term)
        qualified.extend(result)

    logger.info(f"\n✅ {len(qualified)} vídeos qualificados passaram nos critérios")

    if not qualified:
        logger.warning("⚠️ Nenhum vídeo qualificado encontrado. Verifique os critérios ou a cota da API.")
        # Mesmo assim gera um relatório vazio para registrar a execução
    
    # 6. Gera o relatório HTML
    logger.info("📄 Gerando relatório HTML...")
    path = save_report(qualified)
    logger.info(f"🎉 Concluído! Relatório: {path}")


if __name__ == "__main__":
    run()
