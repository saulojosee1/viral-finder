import os
from datetime import datetime, timedelta, timezone

# ── API ───────────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ── Critérios de qualidade ────────────────────────────────────────────────────
CHANNEL_MAX_AGE_DAYS    = 90
VIDEO_MIN_VIEWS         = 100_000
VIDEO_MIN_VIEWS_PER_DAY = 10_000
VIDEO_VIRAL_WINDOW_DAYS = 14

# ── Duração por modo ──────────────────────────────────────────────────────────
SHORTS_MAX_SECONDS = 60
LONG_MIN_SECONDS   = 1200   # 20 min

# ── Exclusões ─────────────────────────────────────────────────────────────────
EXCLUDED_TERMS = [
    "gta 6", "gta6", "gta vi", "grand theft auto 6", "grand theft auto vi",
]

# ── Idiomas de busca ──────────────────────────────────────────────────────────
# Cada entrada: (relevanceLanguage, regionCode, label)
LANGUAGES = [
    ("pt", "BR", "Português 🇧🇷"),
    ("en", "US", "English 🇺🇸"),
    ("es", "ES", "Español 🇪🇸"),
]

# ── Termos de busca por idioma ────────────────────────────────────────────────
# ⚠️ Limite diário: 10.000 units. Cada search.list = 100 units.
# Fórmula: termos × idiomas × modos × 100 ≤ 9.000 (margem para stats)
# 8 termos × 3 idiomas × 2 modos = 48 buscas = 4.800 units → seguro ✅
SEARCH_TERMS = {
    "pt": [
        "tutorial", "como fazer", "review", "gameplay",
        "finanças", "educação", "tecnologia", "motivação",
    ],
    "en": [
        "tutorial", "how to", "review", "gameplay",
        "finance", "education", "technology", "motivation",
    ],
    "es": [
        "tutorial", "como hacer", "review", "gameplay",
        "finanzas", "educación", "tecnología", "motivación",
    ],
}

MAX_RESULTS_PER_TERM = 50

# ── Datas ─────────────────────────────────────────────────────────────────────
NOW = datetime.now(timezone.utc)
CHANNEL_MIN_CREATED    = NOW - timedelta(days=CHANNEL_MAX_AGE_DAYS)
SEARCH_PUBLISHED_AFTER = (NOW - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Saída ─────────────────────────────────────────────────────────────────────
REPORTS_DIR = "reports"

# ── Score de oportunidade para canal dark ─────────────────────────────────────
# Compatibilidade do nicho com produção sem rosto (0–100)
DARK_CHANNEL_COMPAT = {
    "Ciência & Tecnologia": 98,
    "Educação":             97,
    "Notícias & Política":  93,
    "Filme & Animação":     90,
    "Entretenimento":       88,
    "Games":                85,
    "Música":               83,
    "Esportes":             78,
    "Comédia":              72,
    "Finanças":             95,
    "Profissões & Tutoriais": 94,
    "Viagem & Eventos":     60,
    "Culinária":            50,
    "Animais de Estimação": 55,
    "Automóveis":           65,
    "Pessoas & Blogs":      25,
    "Vídeo Blog":           15,
}

DARK_CHANNEL_FORMAT = {
    "Ciência & Tecnologia": "Narração IA + imagens/B-roll + animações",
    "Educação":             "Narração IA + slides + infográficos",
    "Notícias & Política":  "Narração IA + clipes de notícias + texto",
    "Filme & Animação":     "Top listas / recaps narrados + imagens",
    "Entretenimento":       "Top listas + imagens/clipes + narração IA",
    "Games":                "Gameplay gravado + narração IA",
    "Música":               "Compilações / lofi / beats + imagens",
    "Esportes":             "Melhores momentos + narração IA",
    "Comédia":              "Compilações de clips + narração",
    "Finanças":             "Narração IA + gráficos + animações",
    "Profissões & Tutoriais": "Screen recording + narração IA",
    "Viagem & Eventos":     "Imagens de stock + narração IA",
    "Culinária":            "Receitas animadas + narração IA",
    "Animais de Estimação": "Compilações de clips virais",
    "Automóveis":           "Reviews narrados + imagens",
    "Pessoas & Blogs":      "Difícil sem rosto — baixa compatibilidade",
    "Vídeo Blog":           "Requer presença — muito difícil sem rosto",
}
