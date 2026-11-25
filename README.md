# 🔥 Viral Finder

Robô que descobre canais e vídeos virais no YouTube.

## Critérios

| Critério | Regra |
|---|---|
| Idade do canal | ≤ 90 dias desde a criação |
| Views mínimas | ≥ 100.000 views por vídeo |
| Velocidade | ≥ 10.000 views/dia (janela de 14 dias) |
| Excluído | GTA 6 e variações |
| Frequência | 2× por semana (terça e sexta, 08h BRT) |

## Como usar

### Rodar localmente
```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Definir a chave da API
export YOUTUBE_API_KEY="sua_chave_aqui"

# 3. Rodar
python main.py

# 4. Abrir o relatório
open reports/index.html
```

### GitHub Actions (automático)
1. Faça fork/clone deste repositório no GitHub
2. Vá em **Settings → Secrets and variables → Actions → New repository secret**
3. Nome: `YOUTUBE_API_KEY`, Valor: sua chave
4. Habilite o GitHub Pages em **Settings → Pages → Source: GitHub Actions**
5. O robô roda automaticamente toda terça e sexta!
6. Para rodar agora: **Actions → 🔥 Viral Finder → Run workflow**

## Estrutura

```
viral-finder/
├── main.py          # Ponto de entrada
├── config.py        # Configurações e critérios
├── fetcher.py       # Busca na YouTube API
├── filter.py        # Aplica critérios de qualidade
├── reporter.py      # Gera relatório HTML
├── requirements.txt
├── .github/
│   └── workflows/
│       └── viral-finder.yml   # Agendamento automático
└── reports/
    ├── index.html             # Último relatório (GitHub Pages)
    └── report_YYYY-MM-DD.html # Histórico
```
