# YARA

YARA e um assistente virtual de hotel. O repositório ja tem o frontend React/Vite e agora ganhou a primeira camada funcional do MVP:

```text
React intro
  ↓
Streamlit chat
  ↓
CSV estruturado + PDFs do hotel
  ↓
OpenRouter embeddings + LLM
```

O foco agora e o circuito completo do MVP:

```text
Usuario
  ↓
Apresentacao da YARA
  ↓
Iniciar demo
  ↓
Streamlit
  ↓
scenario=1001
  ↓
CSV da reserva
  ↓
PDF -> Markdown -> chunks -> embeddings
  ↓
Top-K similaridade
  ↓
Prompt final
  ↓
OpenRouter LLM
  ↓
Chat da YARA
```

## O que ja esta pronto

- Frontend de apresentacao em `src/components/Intro`
- CTA final que abre a demo do Streamlit
- CSVs estruturados em `data/csv`
- Conversor CSV em `backend/data_processing/csv_loader.py`
- Pipeline PDF -> Markdown em `backend/data_processing/hotel_rag.py`
- Indexacao em `data/index/chunks.jsonl`, `data/index/embeddings.npy` e `data/index/index_meta.json`
- Chat Streamlit com OpenRouter em `backend/api/app.py`

## Como rodar a etapa atual

1. Instale as dependencias de frontend:

```bash
npm install
```

2. Instale a dependencia Python do demo:

```bash
py -3 -m pip install -r requirements.txt
```

3. Gere ou atualize o indice RAG:

```bash
py -3 backend/scripts/build_rag_index.py
```

4. Rode o frontend:

```bash
npm run dev
```

5. Rode a demo Streamlit:

```bash
streamlit run backend/api/app.py
```

## Dados estruturados e PDFs

Os CSVs representam a base operacional do hotel:

- `rooms.csv`
- `reservations.csv`
- `services.csv`

Esses dados entram diretamente no contexto da reserva e permitem responder perguntas como:

- Qual e o quarto da reserva atual?
- O cafe da manha esta incluido?
- O quarto tem frigobar?
- Quais servicos estao cadastrados?

Os PDFs em `data/raw` sao convertidos para Markdown, quebrados em chunks e indexados em `data/index`:

- `hotel_guide.pdf`
- `policies.pdf`
- `services.pdf`

## Scripts uteis

- `py -3 backend/scripts/test_csv.py`
- `py -3 backend/scripts/build_rag_index.py`
- `py -3 backend/scripts/test_rag.py`

## Fluxo atual

```text
CSV da reserva + PDFs do hotel
  ↓
Markdown + chunks
  ↓
Embeddings OpenRouter
  ↓
Similarity search
  ↓
Prompt final
  ↓
OpenRouter LLM
  ↓
Streamlit chat
```
