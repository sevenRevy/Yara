from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

import numpy as np

from backend.data_processing.openrouter_client import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    OpenRouterError,
    chat_completion,
    chat_completion_stream,
    embed_texts,
    get_env,
)
from backend.data_processing.store import format_reservation_summary

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
INDEX_DIR = REPO_ROOT / "data" / "index"
DEFAULT_MAX_WORDS = 700
DEFAULT_OVERLAP_WORDS = 80
DEFAULT_TOP_K = 3

SECTION_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    source: str
    markdown_file: str
    section: str
    title: str
    text: str
    word_count: int


@dataclass(slots=True)
class RetrievedChunk:
    chunk: ChunkRecord
    score: float


@dataclass(slots=True)
class HotelRAG:
    raw_dir: Path
    processed_dir: Path
    index_dir: Path
    embedding_model: str
    llm_model: str
    chunks: list[ChunkRecord]
    embeddings: np.ndarray
    dimensions: int
    built_at: str

    @property
    def is_empty(self) -> bool:
        return not self.chunks or self.embeddings.size == 0

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        if self.is_empty:
            return []

        query_embedding = np.asarray(
            embed_texts([query], model=self.embedding_model)[0],
            dtype=np.float32,
        )
        matrix = np.asarray(self.embeddings, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] == 0:
            return []

        query_norm = float(np.linalg.norm(query_embedding))
        if query_norm == 0:
            return []

        doc_norms = np.linalg.norm(matrix, axis=1)
        safe_denominator = np.where(doc_norms == 0, 1.0, doc_norms * query_norm)
        scores = matrix @ query_embedding / safe_denominator

        ranked_indices = np.argsort(scores)[::-1][:top_k]
        hits: list[RetrievedChunk] = []
        for index in ranked_indices:
            hits.append(
                RetrievedChunk(
                    chunk=self.chunks[int(index)],
                    score=float(scores[int(index)]),
                )
            )
        return hits

    def _compose_documents_block(self, hits: list[RetrievedChunk]) -> str:
        if not hits:
            return "Nenhum trecho adicional foi recuperado dos PDFs processados."

        parts: list[str] = []
        for rank, hit in enumerate(hits, start=1):
            parts.append(
                f"[{rank}] {hit.chunk.source} :: {hit.chunk.section} "
                f"(score={hit.score:.3f})"
            )
            parts.append(hit.chunk.text.strip())
            parts.append("")
        return "\n".join(parts).strip()

    def _build_messages(
        self,
        question: str,
        bundle: dict[str, Any],
        services: list[dict[str, Any]],
        hits: list[RetrievedChunk],
    ) -> list[dict[str, str]]:
        reservation_context = format_reservation_summary(bundle)
        services_context = "\n".join(
            [
                f"- {service['name']}: {service['description']} "
                f"({'incluido' if int(service['included']) == 1 else 'nao incluido'})"
                for service in services
            ]
        )
        retrieved_context = self._compose_documents_block(hits)

        system_prompt = (
            "Voce e a YARA, assistente do hotel. Responda em portugues claro e objetivo.\n"
            "Use os fatos da reserva como fonte primaria para dados pessoais e da estadia.\n"
            "Use os trechos recuperados dos PDFs para politicas, horarios e conhecimento do hotel.\n"
            "Se a resposta nao estiver no contexto, diga isso explicitamente e nao invente."
        )
        user_prompt = (
            f"RESERVA\n{reservation_context}\n\n"
            f"SERVICOS ESTRUTURADOS\n{services_context or 'Nenhum servico cadastrado.'}\n\n"
            f"DOCUMENTOS RECUPERADOS\n{retrieved_context}\n\n"
            f"PERGUNTA\n{question}"
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _local_fallback(
        self,
        question: str,
        bundle: dict[str, Any],
        services: list[dict[str, Any]],
        hits: list[RetrievedChunk],
    ) -> str:
        normalized = question.lower()

        if any(token in normalized for token in {"quarto", "room", "reserva", "hospede"}):
            return (
                f"Voce esta na reserva {bundle['reservation_id']}, hospede {bundle['guest']}, "
                f"no quarto {bundle['room_id']} ({bundle['room_type']}). "
                f"Check-in em {bundle['check_in']} e check-out em {bundle['check_out']}."
            )

        if "piscina" in normalized:
            service = next((item for item in services if str(item["name"]).lower() == "piscina"), None)
            if service is not None:
                return (
                    f"A {str(service['name']).lower()} esta incluida nesta reserva. "
                    f"{service['description']}."
                )

        if "cafe" in normalized or "breakfast" in normalized:
            service = next((item for item in services if "cafe" in str(item["name"]).lower()), None)
            if service is not None:
                return (
                    f"O {str(service['name']).lower()} esta incluido nesta reserva. "
                    f"{service['description']}."
                )

        if "frigobar" in normalized or "minibar" in normalized:
            return (
                "Sim, o quarto tem frigobar. "
                f"O quarto {bundle['room_id']} foi cadastrado com essa comodidade."
            )

        if "servico" in normalized or "servicos" in normalized:
            included = [service["name"] for service in services if int(service["included"]) == 1]
            return "Servicos incluidos no momento: " + ", ".join(included) + "."

        if "checkout" in normalized:
            return f"Seu checkout atual esta previsto para {bundle['check_out']}."

        if hits:
            top = hits[0]
            return (
                "Encontrei contexto relevante nos PDFs, mas o modelo OpenRouter nao respondeu "
                "neste momento. "
                f"Trecho principal: {top.chunk.source} :: {top.chunk.section}. "
                f"{top.chunk.text[:300].strip()}"
            )

        return (
            "Ainda nao encontrei um trecho util nos PDFs processados. "
            "Se a pergunta for sobre a reserva, posso responder com os dados estruturados."
        )

    def answer(self, question: str, bundle: dict[str, Any], services: list[dict[str, Any]]) -> str:
        api_key = get_env("OPENROUTER_API_KEY")
        if not api_key:
            return self._local_fallback(question, bundle, services, [])

        hits = self.retrieve(question)
        messages = self._build_messages(question, bundle, services, hits)
        try:
            return chat_completion(messages, model=self.llm_model)
        except (RuntimeError, OpenRouterError):
            return self._local_fallback(question, bundle, services, hits)

    def answer_stream(
        self,
        question: str,
        bundle: dict[str, Any],
        services: list[dict[str, Any]],
    ) -> Iterator[str]:
        api_key = get_env("OPENROUTER_API_KEY")
        if not api_key:
            yield self._local_fallback(question, bundle, services, [])
            return

        hits = self.retrieve(question)
        messages = self._build_messages(question, bundle, services, hits)
        try:
            yield from chat_completion_stream(messages, model=self.llm_model)
        except (RuntimeError, OpenRouterError):
            yield self._local_fallback(question, bundle, services, hits)


def _split_words(text: str, max_words: int, overlap_words: int) -> Iterable[str]:
    words = text.split()
    if not words:
        return []

    step = max(1, max_words - overlap_words)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        segment = words[start : start + max_words]
        if not segment:
            break
        chunks.append(" ".join(segment))
        if start + max_words >= len(words):
            break
        start += step
    return chunks


def _split_markdown_sections(markdown: str, fallback_title: str) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    heading_stack: list[str] = []
    body_lines: list[str] = []

    def flush() -> None:
        if not body_lines and not heading_stack:
            return
        section_path = " / ".join(heading_stack) if heading_stack else fallback_title
        title = heading_stack[-1] if heading_stack else fallback_title
        body = "\n".join(body_lines).strip()
        if body:
            sections.append((section_path, title, body))

    for line in markdown.splitlines():
        match = SECTION_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            heading_stack[:] = heading_stack[: level - 1]
            heading_stack.append(heading)
            body_lines = []
            continue
        body_lines.append(line)

    flush()
    if sections:
        return sections

    cleaned = markdown.strip()
    if cleaned:
        sections.append((fallback_title, fallback_title, cleaned))
    return sections


def _markdown_to_chunks(
    markdown: str,
    *,
    source: str,
    markdown_file: str,
    max_words: int = DEFAULT_MAX_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[ChunkRecord]:
    section_blocks = _split_markdown_sections(markdown, fallback_title=Path(source).stem)
    chunks: list[ChunkRecord] = []

    for section_index, (section_path, title, body) in enumerate(section_blocks, start=1):
        text_blocks = list(_split_words(body, max_words=max_words, overlap_words=overlap_words))
        if not text_blocks:
            continue

        for part_index, text_block in enumerate(text_blocks, start=1):
            chunk_text = f"# {title}\n\n{text_block}".strip()
            chunk_id = f"{Path(source).stem}_{section_index:03d}_{part_index:03d}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    source=source,
                    markdown_file=markdown_file,
                    section=section_path,
                    title=title,
                    text=chunk_text,
                    word_count=len(chunk_text.split()),
                )
            )

    return chunks


def _extract_markdown_from_pdf(pdf_path: Path) -> str:
    os.environ.setdefault("TORCHINDUCTOR_DISABLE", "1")
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

    try:
        import torch

        try:
            torch._dynamo.disable()
        except Exception:
            pass
        if hasattr(torch, "compile"):
            torch.compile = lambda model, *args, **kwargs: model  # type: ignore[assignment]
    except Exception:
        pass

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions(
        ocr_batch_size=64,
        layout_batch_size=64,
        table_batch_size=64,
    )
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )
    result = converter.convert(str(pdf_path))
    document = getattr(result, "document", None)
    if document is None:
        return ""
    return document.export_to_markdown()


def _relative_posix(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def process_pdfs_to_markdown(
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
) -> list[Path]:
    processed_dir.mkdir(parents=True, exist_ok=True)
    for stale_markdown in processed_dir.glob("*.md"):
        if stale_markdown.name != ".gitkeep":
            stale_markdown.unlink()
    pdf_paths = sorted(raw_dir.glob("*.pdf"))
    markdown_paths: list[Path] = []

    for pdf_path in pdf_paths:
        markdown_text = _extract_markdown_from_pdf(pdf_path)
        markdown_path = processed_dir / f"{pdf_path.stem}.md"
        markdown_path.write_text(markdown_text.strip() + "\n", encoding="utf-8")
        markdown_paths.append(markdown_path)

    return markdown_paths


def _load_markdown_files(processed_dir: Path) -> list[Path]:
    return sorted(
        path for path in processed_dir.glob("*.md") if path.is_file() and path.name != ".gitkeep"
    )


def _read_markdown_text(markdown_path: Path) -> str:
    return markdown_path.read_text(encoding="utf-8").strip()


def build_chunks(
    processed_dir: Path = PROCESSED_DIR,
) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    markdown_files = _load_markdown_files(processed_dir)

    for markdown_file in markdown_files:
        text = _read_markdown_text(markdown_file)
        if not text:
            continue
        source_name = markdown_file.stem + ".pdf"
        chunks.extend(
            _markdown_to_chunks(
                text,
                source=source_name,
                markdown_file=_relative_posix(markdown_file),
            )
        )

    return chunks


def _source_fingerprint(raw_dir: Path) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for pdf_path in sorted(raw_dir.glob("*.pdf")):
        stat = pdf_path.stat()
        sources.append(
            {
                "path": _relative_posix(pdf_path),
                "mtime": stat.st_mtime,
                "size": stat.st_size,
            }
        )
    return sources


def _source_identity(sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "path": source.get("path"),
            "size": source.get("size"),
        }
        for source in sources
    ]


def _index_files_exist(index_dir: Path) -> bool:
    return (
        (index_dir / "chunks.jsonl").exists()
        and (index_dir / "embeddings.npy").exists()
        and (index_dir / "index_meta.json").exists()
    )


def _load_meta(index_dir: Path) -> dict[str, Any] | None:
    meta_path = index_dir / "index_meta.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _needs_rebuild(raw_dir: Path, processed_dir: Path, index_dir: Path) -> bool:
    if not _index_files_exist(index_dir):
        return True

    meta = _load_meta(index_dir)
    if not meta:
        return True

    recorded_sources = meta.get("sources") or []
    current_sources = _source_fingerprint(raw_dir)
    if _source_identity(recorded_sources) != _source_identity(current_sources):
        return True

    return False


def _write_chunks_jsonl(index_dir: Path, chunks: list[ChunkRecord]) -> Path:
    chunks_path = index_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(
                json.dumps(
                    {
                        "chunk_id": chunk.chunk_id,
                        "source": chunk.source,
                        "markdown_file": chunk.markdown_file,
                        "section": chunk.section,
                        "title": chunk.title,
                        "text": chunk.text,
                        "word_count": chunk.word_count,
                    },
                    ensure_ascii=False,
                )
            )
            handle.write("\n")
    return chunks_path


def _write_embeddings(index_dir: Path, embeddings: np.ndarray) -> Path:
    embeddings_path = index_dir / "embeddings.npy"
    np.save(embeddings_path, embeddings.astype(np.float32, copy=False))
    return embeddings_path


def _write_meta(
    index_dir: Path,
    *,
    embedding_model: str,
    llm_model: str,
    chunks: list[ChunkRecord],
    dimensions: int,
    sources: list[dict[str, Any]],
) -> Path:
    meta_path = index_dir / "index_meta.json"
    payload = {
        "embedding_model": embedding_model,
        "llm_model": llm_model,
        "documents": len(sources),
        "chunks": len(chunks),
        "dimensions": dimensions,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
    }
    meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


def build_hotel_index(
    *,
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    index_dir: Path = INDEX_DIR,
    embedding_model: str | None = None,
    llm_model: str | None = None,
) -> HotelRAG:
    embedding_model = embedding_model or get_env("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    llm_model = llm_model or get_env("LLM_MODEL", DEFAULT_LLM_MODEL)

    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    process_pdfs_to_markdown(raw_dir=raw_dir, processed_dir=processed_dir)
    chunks = build_chunks(processed_dir=processed_dir)
    sources = _source_fingerprint(raw_dir)

    if chunks:
        embeddings_list = embed_texts([chunk.text for chunk in chunks], model=embedding_model)
        embeddings = np.asarray(embeddings_list, dtype=np.float32)
        dimensions = int(embeddings.shape[1]) if embeddings.ndim == 2 and embeddings.shape[0] else 0
    else:
        embeddings = np.empty((0, 0), dtype=np.float32)
        dimensions = 0

    _write_chunks_jsonl(index_dir, chunks)
    _write_embeddings(index_dir, embeddings)
    _write_meta(
        index_dir,
        embedding_model=embedding_model,
        llm_model=llm_model,
        chunks=chunks,
        dimensions=dimensions,
        sources=sources,
    )

    return HotelRAG(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        index_dir=index_dir,
        embedding_model=embedding_model,
        llm_model=llm_model,
        chunks=chunks,
        embeddings=embeddings,
        dimensions=dimensions,
        built_at=datetime.now(timezone.utc).isoformat(),
    )


def _load_chunks(index_dir: Path) -> list[ChunkRecord]:
    chunks_path = index_dir / "chunks.jsonl"
    if not chunks_path.exists():
        return []

    chunks: list[ChunkRecord] = []
    for raw_line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        data = json.loads(raw_line)
        chunks.append(
            ChunkRecord(
                chunk_id=data["chunk_id"],
                source=data["source"],
                markdown_file=data["markdown_file"],
                section=data["section"],
                title=data["title"],
                text=data["text"],
                word_count=int(data["word_count"]),
            )
        )
    return chunks


def _load_embeddings(index_dir: Path) -> np.ndarray:
    embeddings_path = index_dir / "embeddings.npy"
    if not embeddings_path.exists():
        return np.empty((0, 0), dtype=np.float32)
    return np.load(embeddings_path, allow_pickle=False)


def load_hotel_rag(
    *,
    raw_dir: Path = RAW_DIR,
    processed_dir: Path = PROCESSED_DIR,
    index_dir: Path = INDEX_DIR,
    rebuild: bool = False,
) -> HotelRAG:
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    if rebuild or _needs_rebuild(raw_dir, processed_dir, index_dir):
        return build_hotel_index(
            raw_dir=raw_dir,
            processed_dir=processed_dir,
            index_dir=index_dir,
        )

    meta = _load_meta(index_dir) or {}
    return HotelRAG(
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        index_dir=index_dir,
        embedding_model=str(meta.get("embedding_model") or DEFAULT_EMBEDDING_MODEL),
        llm_model=str(meta.get("llm_model") or DEFAULT_LLM_MODEL),
        chunks=_load_chunks(index_dir),
        embeddings=_load_embeddings(index_dir),
        dimensions=int(meta.get("dimensions") or 0),
        built_at=str(meta.get("built_at") or ""),
    )
