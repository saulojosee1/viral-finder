import os
from datetime import datetime, timedelta, timezone

# ── API ───────────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ── Critérios de qualidade (garimpagem ampliada para canais dark) ─────────────
CHANNEL_MAX_AGE_DAYS       = 180     # canais criados há no máximo 6 meses
VIDEO_MIN_VIEWS            = 30_000  # mínimo de 30k views por vídeo
VIDEO_MIN_VIEWS_PER_DAY    = 1_500   # velocidade média mínima desde a publicação
VIDEO_MIN_DURATION_SECONDS = 480     # 8 minutos ou mais (médios + longos narrados)

# ── Exclusões (GTA 6 + formatos com rosto/podcast/react/gameplay) ─────────────
EXCLUDED_TERMS = [
    # Jogos / GTA 6
    "gta 6", "gta6", "gta vi", "grand theft auto 6", "grand theft auto vi",
    # Formatos não-dark / com rosto / cortes / gameplay
    "podcast", "cortes", "podcast clip", "vlog", "daily vlog",
    "react", "reaction", "reagindo", "reaccionando",
    "gameplay", "walkthrough", "playthrough", "let's play", "lets play",
    "livestream", "live stream", "ao vivo", "en vivo",
    "entrevista", "interview", "#shorts",
]

# ── Idiomas de busca ──────────────────────────────────────────────────────────
LANGUAGES = [
    ("pt", "BR", "Português 🇧🇷"),
    ("en", "US", "English 🇺🇸"),
    ("es", "ES", "Español 🇪🇸"),
]

# ── Termos de busca por idioma (nichos dark: UFO, mistérios, true crime, etc.) ─
# Cota: 7 termos × 3 idiomas × 2 faixas (medium + long) × 100 = 4.200 units/run
# Limite diário gratuito: 10.000 units → margem segura para até 2 runs/dia
SEARCH_TERMS = {
    "pt": [
        "ovnis misterio",
        "misterios inexplicaveis",
        "iceberg explicado",
        "caso criminal real",
        "desaparecimento misterioso",
        "historia oculta civilizacoes",
        "relatos sobrenaturais terror",
    ],
    "en": [
        "ufo alien documentary",
        "unsolved mystery documentary",
        "iceberg explained",
        "true crime documentary",
        "mysterious disappearance",
        "forbidden history ancient",
        "scary true stories paranormal",
    ],
    "es": [
        "ovnis misterio real",
        "misterios sin resolver",
        "iceberg explicado",
        "crimen real caso",
        "desaparicion misteriosa",
        "historia oculta prohibida",
        "historias terror reales paranormal",
    ],
}

# Faixas buscadas na YouTube API para cobrir tudo >= 8 min (4-20 min + >20 min)
DURATION_BUCKETS = ["medium", "long"]

MAX_RESULTS_PER_TERM = 50

# ── Datas ─────────────────────────────────────────────────────────────────────
NOW = datetime.now(timezone.utc)
CHANNEL_MIN_CREATED    = NOW - timedelta(days=CHANNEL_MAX_AGE_DAYS)
SEARCH_PUBLISHED_AFTER = (NOW - timedelta(days=CHANNEL_MAX_AGE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")

# ── Saída ─────────────────────────────────────────────────────────────────────
REPORTS_DIR = "reports"

# ── Subnichos Dark (classificação automática + compatibilidade/formato) ────────
DARK_SUBNICHES = [
    ("UFOs & Espaço", [
        "ufo", "ovnis", "ovni", "alien", "aliens", "extraterrestre", "uap",
        "area 51", "nasa", "space", "universo", "espaço", "espacio", "cosmos", "planet",
    ]),
    ("Casos Policiais & True Crime", [
        "true crime", "crimen", "crime", "criminal", "murder", "killer", "serial",
        "homicidio", "assassin", "policial", "fbi", "detective", "cold case",
        "desaparec", "missing", "kidnap", "sequestro", "bodycam", "interrogation",
    ]),
    ("Mistérios & Icebergs", [
        "mystery", "mysteries", "misterio", "misterios", "mistério", "mistérios",
        "unsolved", "unexplained", "inexplicav", "sin resolver", "iceberg",
        "strange", "bizarre", "conspirac", "what really happened", "creepy mystery",
    ]),
    ("História Oculta & Lugares Proibidos", [
        "forbidden", "proibido", "prohibid", "ancient", "antiga", "antigua",
        "civilizac", "civilization", "lost city", "arqueolog", "archaeolog",
        "historia oculta", "hidden history", "secret history", "bunker", "titanic",
        "chernobyl", "catastrophe", "disaster", "desastre", "deep sea", "mariana trench",
    ]),
    ("Terror & Sobrenatural", [
        "horror", "terror", "scary", "paranormal", "ghost", "fantasma", "haunted",
        "assombra", "sobrenatural", "urban legend", "lenda urbana", "leyenda",
        "cryptid", "skinwalker", "demon", "creepy", "nightmare", "backrooms",
    ]),
]

DARK_CHANNEL_COMPAT = {
    "UFOs & Espaço":                       98,
    "Mistérios & Icebergs":                97,
    "Casos Policiais & True Crime":        95,
    "História Oculta & Lugares Proibidos": 96,
    "Terror & Sobrenatural":               94,
    "Ciência & Tecnologia":                90,
    "Educação":                            88,
    "Entretenimento":                      80,
}

DARK_CHANNEL_FORMAT = {
    "UFOs & Espaço":                       "Narração grave + arquivos/clipes UFO + animações 3D espaciais",
    "Mistérios & Icebergs":                "Estrutura de camadas/tópicos + B-roll sombrio + documentos na tela",
    "Casos Policiais & True Crime":        "Linha do tempo + fotos/mapas/arquivos policiais + narração investigativa",
    "História Oculta & Lugares Proibidos": "Documentário narrado + mapas antigos + imagens de satélite/stock",
    "Terror & Sobrenatural":               "Storytelling em 1ª/3ª pessoa + sound design tenso + arte sombria",
}
