"""
fetcher.py — Busca dados na YouTube Data API v3
"""
import time
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

logger = logging.getLogger(__name__)


def get_youtube_client():
    return build("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)


def search_recent_videos(youtube, query: str, published_after: str, video_duration: str = "any") -> list[dict]:
    """Busca vídeos recentes para um termo.
    video_duration: 'any' | 'short' (< 4min) | 'medium' (4-20min) | 'long' (> 20min)
    """
    try:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            publishedAfter=published_after,
            maxResults=config.MAX_RESULTS_PER_TERM,
            videoDuration=video_duration,
            regionCode="BR",
            relevanceLanguage="pt",
        ).execute()
        return [
            {
                "videoId": item["id"]["videoId"],
                "channelId": item["snippet"]["channelId"],
                "title": item["snippet"]["title"],
                "publishedAt": item["snippet"]["publishedAt"],
                "channelTitle": item["snippet"]["channelTitle"],
                "description": item["snippet"].get("description", ""),
                "tags": item["snippet"].get("tags", []),
            }
            for item in response.get("items", [])
        ]
    except HttpError as e:
        logger.error(f"Erro na busca '{query}': {e}")
        return []


def get_video_stats(youtube, video_ids: list[str]) -> dict[str, dict]:
    """Retorna estatísticas detalhadas + duração de até 50 vídeos por chamada."""
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            response = youtube.videos().list(
                part="statistics,snippet,contentDetails",
                id=",".join(batch),
            ).execute()
            for item in response.get("items", []):
                vid = item["id"]
                s = item.get("statistics", {})
                snippet = item.get("snippet", {})
                content = item.get("contentDetails", {})
                stats[vid] = {
                    "viewCount":     int(s.get("viewCount", 0)),
                    "likeCount":     int(s.get("likeCount", 0)),
                    "commentCount":  int(s.get("commentCount", 0)),
                    "publishedAt":   snippet.get("publishedAt", ""),
                    "categoryId":    snippet.get("categoryId", ""),
                    "tags":          snippet.get("tags", []),
                    "title":         snippet.get("title", ""),
                    "channelTitle":  snippet.get("channelTitle", ""),
                    "channelId":     snippet.get("channelId", ""),
                    "thumbnailUrl":  snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "duration":      content.get("duration", "PT0S"),  # ISO 8601 ex: PT1M30S
                }
        except HttpError as e:
            logger.error(f"Erro ao buscar stats de vídeos: {e}")
        time.sleep(0.1)
    return stats


def get_channel_details(youtube, channel_ids: list[str]) -> dict[str, dict]:
    """Retorna detalhes de canais (data de criação, inscritos, etc.)."""
    details = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        try:
            response = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(batch),
            ).execute()
            for item in response.get("items", []):
                cid = item["id"]
                s = item.get("statistics", {})
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
            logger.error(f"Erro ao buscar canais: {e}")
        time.sleep(0.1)
    return details
