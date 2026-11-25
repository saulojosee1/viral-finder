import os
from datetime import datetime, timedelta, timezone

# ── API ──────────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ── Critérios de qualidade ────────────────────────────────────────────────────
CHANNEL_MAX_AGE_DAYS      = 90       # canal criado há no máximo X dias
VIDEO_MIN_VIEWS           = 100_000  # vídeo precisa de no mínimo X views
VIDEO_MIN_VIEWS_PER_DAY   = 10_000  # velocidade: views/dia na janela abaixo
VIDEO_VIRAL_WINDOW_DAYS   = 14       # janela para medir velocidade de viralização

# ── Duração por modo ──────────────────────────────────────────────────────────
SHORTS_MAX_SECONDS  = 60    # Shorts: até 60 segundos
LONG_MIN_SECONDS    = 1200  # Vídeos longos: mais de 20 minutos

# ── Exclusões ─────────────────────────────────────────────────────────────────
EXCLUDED_TERMS = [
    "gta 6", "gta6", "gta vi", "grand theft auto 6", "grand theft auto vi",
]

# ── Busca ─────────────────────────────────────────────────────────────────────
SEARCH_TERMS = [
    "tutorial", "review", "como fazer", "vlog", "unboxing",
    "receita", "gameplay", "fitness", "tecnologia", "finanças",
    "empreendedorismo", "moda", "beleza", "viagem", "humor",
    "educação", "ciência", "política", "esporte", "música",
]

MAX_RESULTS_PER_TERM = 50   # max permitido pela API por chamada

# ── Datas ─────────────────────────────────────────────────────────────────────
NOW = datetime.now(timezone.utc)
CHANNEL_MIN_CREATED = NOW - timedelta(days=CHANNEL_MAX_AGE_DAYS)
SEARCH_PUBLISHED_AFTER = (NOW - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Saída ─────────────────────────────────────────────────────────────────────
REPORTS_DIR = "reports"
