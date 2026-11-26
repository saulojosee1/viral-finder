"""
fetcher.py — Busca dados na YouTube Data API v3 (com trava explícita de cota)
"""
import json
import time
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

logger = logging.getLogger(__name__)


class YouTubeAPIError(RuntimeError):
    """Erro crítico da YouTube API (ex: cota esgotada ou chave inválida)."""


def _check_fatal_http_error(err: HttpError, context: str):
    reason = ""
    try:
        payload = json.loads(err.content.decode("utf-8"))
        errors = payload.get("error", {}).get("errors", [])
        if errors:
            reason = errors[0].get("reason", "")
    except Exception:
        pass

    if reason in {"quotaExceeded", "dailyLimitExceeded", "keyInvalid", "accessNotConfigured"} or err.resp.status == 403:
        raise YouTubeAPIError(f"Erro fatal na YouTube API ({context}) [{reason or err.resp.status}]: {err}")


def get_youtube_client():
    return build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def search_recent_videos(youtube, query: str, published_after: str,
                         video_duration: str = "medium",
                         lang: str = "pt", region: str = "BR") -> list[dict]:
    """Busca vídeos recentes para um termo, faixa de duração e idioma."""
    try:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            publishedAfter=published_after,
            maxResults=config.MAX_RESULTS_PER_TERM,
            videoDuration=video_duration,
            relevanceLanguage=lang,
            regionCode=region,
        ).execute()
        return [
            {
                "videoId":      item["id"]["videoId"],
                "channelId":    item["snippet"]["channelId"],
                "title":        item["snippet"]["title"],
                "publishedAt":  item["snippet"]["publishedAt"],
                "channelTitle": item["snippet"]["channelTitle"],
                "description":  item["snippet"].get("description", ""),
                "language":     lang,
                "region":       region,
            }
            for item in response.get("items", [])
        ]
    except HttpError as e:
        _check_fatal_http_error(e, f"search '{query}' [{lang}/{video_duration}]")
        logger.error(f"Erro na busca '{query}' [{lang}/{video_duration}]: {e}")
        return []


def get_video_stats(youtube, video_ids: list[str]) -> dict[str, dict]:
    """Retorna estatísticas + duração de até 50 vídeos por chamada."""
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            response = youtube.videos().list(
                part="statistics,snippet,contentDetails",
                id=",".join(batch),
            ).execute()
            for item in response.get("items", []):
                vid = item["id"]
                s       = item.get("statistics", {})
                snippet = item.get("snippet", {})
                content = item.get("contentDetails", {})
                stats[vid] = {
                    "viewCount":            int(s.get("viewCount", 0)),
                    "likeCount":            int(s.get("likeCount", 0)),
                    "commentCount":         int(s.get("commentCount", 0)),
                    "publishedAt":          snippet.get("publishedAt", ""),
                    "categoryId":           snippet.get("categoryId", ""),
                    "tags":                 snippet.get("tags", []),
                    "title":                snippet.get("title", ""),
                    "description":          snippet.get("description", ""),
                    "channelTitle":         snippet.get("channelTitle", ""),
                    "channelId":            snippet.get("channelId", ""),
                    "thumbnailUrl":         snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "duration":             content.get("duration", "PT0S"),
                    "defaultAudioLanguage": snippet.get("defaultAudioLanguage", ""),
                    "defaultLanguage":      snippet.get("defaultLanguage", ""),
                }
        except HttpError as e:
            _check_fatal_http_error(e, "videos.list")
            logger.error(f"Erro ao buscar stats: {e}")
        time.sleep(0.1)
    return stats


def get_channel_details(youtube, channel_ids: list[str]) -> dict[str, dict]:
    """Retorna detalhes de canais."""
    details = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        try:
            response = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(batch),
            ).execute()
            for item in response.get("items", []):
                cid     = item["id"]
                s       = item.get("statistics", {})
                snippet = item.get("snippet", {})
                details[cid] = {
                    "channelTitle":    snippet.get("title", ""),
                    "createdAt":       snippet.get("publishedAt", ""),
                    "subscriberCount": int(s.get("subscriberCount", 0)),
                    "videoCount":      int(s.get("videoCount", 0)),
                    "viewCount":       int(s.get("viewCount", 0)),
                    "thumbnailUrl":    snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "country":         snippet.get("country", ""),
                }
        except HttpError as e:
            _check_fatal_http_error(e, "channels.list")
            logger.error(f"Erro ao buscar canais: {e}")
        time.sleep(0.1)
    return details
