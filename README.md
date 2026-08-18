# YARA

YARA e um assistente virtual de hotel. O repositório ja tem o frontend React/Vite e agora ganhou a primeira camada funcional do MVP:

```text
React intro
  ↓
Streamlit demo
  ↓
SQLite com reservas, quartos e servicos
```

O foco desta etapa e validar o fluxo de entrada antes do RAG:

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
SQLite
  ↓
Chat estruturado
```

## O que ja esta pronto

- Frontend de apresentacao em `src/components/Intro`
- CTA final que abre a demo do Streamlit
- CSV de exemplo em `data/raw`
- Bootstrap do SQLite em `backend/data_processing/store.py`
- Demo Streamlit em `backend/api/app.py`

## Como rodar a etapa atual

1. Instale as dependencias de frontend:

```bash
npm install
```

2. Instale a dependencia Python do demo:

```bash
py -3 -m pip install -r requirements.txt
```

3. Gere o banco SQLite de exemplo:

```bash
py -3 backend/scripts/bootstrap_demo.py
```

4. Rode o frontend:

```bash
npm run dev
```

5. Rode a demo Streamlit:

```bash
streamlit run backend/api/app.py
```

## Dados estruturados

Os CSVs representam a base operacional do hotel:

- `rooms.csv`
- `reservations.csv`
- `services.csv`

Esses dados entram no SQLite e permitem responder perguntas como:

- Qual e o quarto da reserva atual?
- O cafe da manha esta incluido?
- O quarto tem frigobar?
- Quais servicos estao cadastrados?

## Proxima fase

Depois desta base, o proximo passo natural e adicionar:

```text
PDF -> Markdown -> chunking -> embeddings -> retrieval -> prompt
```

Nessa etapa o Streamlit continua responsavel pela interface e pela sessao, enquanto a camada textual do hotel entra como contexto complementar.
