from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from assistant_core.config import Settings
from assistant_core.llm import build_embeddings


class KnowledgeBase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._chunks: list[Document] | None = None
        self._vector_store: FAISS | None = None
        self._vector_signature: dict[str, int] | None = None

    def build_context(self, query: str, limit: int) -> tuple[str, list[str]]:
        results = self.search(query, limit)
        if not results:
            return ("No relevant personal documents found.", [])
        return (self._render_documents(results), self._source_labels(results))

    def render_context(self, query: str, limit: int) -> str:
        rendered_context, _ = self.build_context(query, limit)
        return rendered_context

    def search(self, query: str, limit: int) -> list[Document]:
        if self.settings.has_model_credentials:
            vector_store = self._load_or_build_vector_store()
            if vector_store is not None:
                return vector_store.similarity_search(query or "personal context", k=limit)
        return self._keyword_search(query, limit)

    def _load_or_build_vector_store(self) -> FAISS | None:
        chunks = self._load_chunks()
        if not chunks:
            return None

        current_signature = self._current_signature()
        if self._vector_store is not None and self._vector_signature == current_signature:
            return self._vector_store

        manifest = self._read_manifest()
        if (
            manifest == current_signature
            and (self.settings.vector_store_dir / "index.faiss").exists()
            and (self.settings.vector_store_dir / "index.pkl").exists()
        ):
            self._vector_store = FAISS.load_local(
                str(self.settings.vector_store_dir),
                build_embeddings(self.settings),
                allow_dangerous_deserialization=True,
            )
            self._vector_signature = current_signature
            return self._vector_store

        self._vector_store = FAISS.from_documents(chunks, build_embeddings(self.settings))
        self._vector_store.save_local(str(self.settings.vector_store_dir))
        self.settings.vector_manifest_file.write_text(
            json.dumps(current_signature, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        self._vector_signature = current_signature
        return self._vector_store

    def _load_chunks(self) -> list[Document]:
        if self._chunks is not None:
            return self._chunks

        documents: list[Document] = []
        for file_path in self._document_files():
            text = file_path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            source = file_path.relative_to(self.settings.root_dir).as_posix()
            documents.append(Document(page_content=text, metadata={"source": source}))

        if not documents:
            self._chunks = []
            return self._chunks

        splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
        self._chunks = splitter.split_documents(documents)
        return self._chunks

    def _keyword_search(self, query: str, limit: int) -> list[Document]:
        chunks = self._load_chunks()
        if not chunks:
            return []

        query_terms = [
            term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2
        ]
        if not query_terms:
            return chunks[:limit]

        scored_chunks: list[tuple[int, Document]] = []
        for chunk in chunks:
            text = chunk.page_content.lower()
            score = sum(text.count(term) for term in query_terms)
            if score:
                scored_chunks.append((score, chunk))

        if not scored_chunks:
            return chunks[:limit]

        scored_chunks.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:limit]]

    def _render_documents(self, documents: list[Document]) -> str:
        rendered = []
        for index, document in enumerate(documents, start=1):
            source = document.metadata.get("source", "unknown")
            rendered.append(f"[{index}] {source}\n{document.page_content.strip()}")
        return "\n\n".join(rendered)

    def _source_labels(self, documents: list[Document]) -> list[str]:
        source_paths = []
        for document in documents:
            source = str(document.metadata.get("source", "")).strip()
            if source and source not in source_paths:
                source_paths.append(source)

        if not source_paths:
            return []

        file_names = [Path(source).name for source in source_paths]
        name_counts = Counter(file_names)
        return [
            Path(source).name if name_counts[Path(source).name] == 1 else source
            for source in source_paths
        ]

    def _document_files(self) -> list[Path]:
        return sorted(
            path
            for path in self.settings.docs_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}
        )

    def _current_signature(self) -> dict[str, int]:
        return {
            path.relative_to(self.settings.root_dir).as_posix(): path.stat().st_mtime_ns
            for path in self._document_files()
        }

    def _read_manifest(self) -> dict[str, int] | None:
        if not self.settings.vector_manifest_file.exists():
            return None
        try:
            return json.loads(
                self.settings.vector_manifest_file.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError:
            return None
