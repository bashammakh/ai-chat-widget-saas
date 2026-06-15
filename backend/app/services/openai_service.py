"""Thin wrapper around the OpenAI SDK for vector stores and the Responses API.

All RAG logic lives here so the routers stay transport-only. The system prompt
forces the model to answer strictly from retrieved knowledge and to fall back to
a fixed "not found" message rather than hallucinating.
"""
from __future__ import annotations

import io
import logging
from typing import Iterable

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I could not find that information in the knowledge base."
# Machine-readable sentinel the model must emit when the answer is not in the
# knowledge base. It is never shown to the user — the backend maps it to a
# structured ``found=false`` flag so the widget can render its own UI.
NO_ANSWER_TOKEN = "<<NO_ANSWER>>"

# Delimiter separating the model's natural answer from the verbatim source
# Q&A reference. The backend splits on it to insert the source line in between.
REF_DELIM = "###REF###"

SYSTEM_PROMPT = (
    "You are a customer-support assistant for a specific company. The company's "
    "knowledge base is organized as question-and-answer (FAQ) entries. "
    "Use ONLY the content returned by the file_search tool. Do not use outside or "
    "prior knowledge.\n"
    "For every user message do EXACTLY this:\n"
    "1) Write a clear, well-phrased, helpful answer to the user's question in the "
    "user's own language (English or Arabic). You may rephrase for clarity.\n"
    f"2) Then output a line containing ONLY this delimiter: {REF_DELIM}\n"
    "3) After the delimiter, attach the matching source entry/entries EXACTLY as "
    "written in the knowledge base (verbatim — do not change wording, numbers, "
    "links, or formatting), each formatted as:\n"
    "❓ <the question, verbatim>\n"
    "<the answer, verbatim>\n"
    "If the user's message maps to MULTIPLE entries, attach ALL of them, each as "
    "its own block separated by a blank line.\n"
    f"If the knowledge base does not contain the answer, reply with EXACTLY this "
    f"token and nothing else: {NO_ANSWER_TOKEN} (do NOT translate it, no delimiter, "
    "no other text). Never invent content not present in the sources."
)

# Clients are cached per API key so rotating the key (from the admin panel)
# transparently switches to a fresh client without a restart.
_clients: dict[str, OpenAI] = {}


def get_client(api_key: str | None = None) -> OpenAI:
    key = api_key or settings.openai_api_key
    client = _clients.get(key)
    if client is None:
        client = OpenAI(api_key=key)
        _clients[key] = client
    return client


def _vector_stores(client: OpenAI):
    """Return the vector_stores resource, tolerating SDK location changes."""
    if hasattr(client, "vector_stores"):
        return client.vector_stores
    return client.beta.vector_stores  # older SDKs


def create_vector_store(name: str, api_key: str | None = None) -> str:
    """Create a new vector store and return its id."""
    client = get_client(api_key)
    vs = _vector_stores(client).create(name=name)
    logger.info("Created vector store %s for %s", vs.id, name)
    return vs.id


def upload_markdown_files(
    vector_store_id: str,
    files: Iterable[tuple[str, bytes]],
    api_key: str | None = None,
) -> list[tuple[str, str]]:
    """Upload markdown files to OpenAI and attach them to the vector store.

    Returns a list of (filename, openai_file_id) tuples. Uses the batched
    upload-and-poll helper so the caller knows indexing has finished.
    """
    client = get_client(api_key)
    results: list[tuple[str, str]] = []

    for filename, content in files:
        buffer = io.BytesIO(content)
        buffer.name = filename  # OpenAI infers the extension from .name
        oa_file = client.files.create(file=buffer, purpose="assistants")
        results.append((filename, oa_file.id))

    file_ids = [fid for _, fid in results]
    if file_ids:
        _vector_stores(client).file_batches.create_and_poll(
            vector_store_id=vector_store_id, file_ids=file_ids
        )
        logger.info(
            "Attached %d file(s) to vector store %s", len(file_ids), vector_store_id
        )
    return results


def delete_file(
    vector_store_id: str | None, openai_file_id: str, api_key: str | None = None
) -> None:
    """Detach a file from the vector store and delete it from OpenAI.

    Best-effort: storage cleanup failures are logged but never block the DB
    delete the caller performs afterwards.
    """
    client = get_client(api_key)
    if vector_store_id:
        try:
            _vector_stores(client).files.delete(
                vector_store_id=vector_store_id, file_id=openai_file_id
            )
        except Exception as exc:  # pragma: no cover - best effort
            logger.warning(
                "Failed to detach file %s from %s: %s",
                openai_file_id, vector_store_id, exc,
            )
    try:
        client.files.delete(openai_file_id)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Failed to delete OpenAI file %s: %s", openai_file_id, exc)


def delete_vector_store(vector_store_id: str, api_key: str | None = None) -> None:
    """Best-effort deletion of a vector store (used on customer teardown)."""
    client = get_client(api_key)
    try:
        _vector_stores(client).delete(vector_store_id=vector_store_id)
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logger.warning("Failed to delete vector store %s: %s", vector_store_id, exc)


def _extract_sources(response) -> list[dict[str, str]]:
    """Collect the distinct files that file_search actually cited.

    Returns a list of {"file_id", "filename"} dicts, read from the message
    annotations returned by the API (not the model's text) so the sources are
    factual and can't be invented. The caller maps file ids to friendly
    display names.
    """
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", None) or []:
            for ann in getattr(content, "annotations", None) or []:
                if getattr(ann, "type", None) == "file_citation":
                    file_id = getattr(ann, "file_id", None) or ""
                    filename = getattr(ann, "filename", None) or ""
                    key = file_id or filename
                    if key and key not in seen:
                        seen.add(key)
                        sources.append({"file_id": file_id, "filename": filename})
    return sources


def has_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


def append_sources(answer: str, names: list[str]) -> str:
    """Append a localized source line listing the given source names."""
    if not names:
        return answer
    if has_arabic(answer):
        return answer + "\n\n📄 المصدر: " + "، ".join(names)
    return answer + "\n\n📄 Source: " + ", ".join(names)


def generate_answer(
    vector_store_id: str,
    message: str,
    history: list[dict[str, str]] | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> tuple[str, bool, list[dict[str, str]], str]:
    """Run the Responses API with file_search scoped to one vector store.

    ``history`` is a list of {"role": "user"|"assistant", "content": str} dicts
    representing earlier turns in the same session (conversation memory).

    Returns ``(answer, found, sources, reference)``:
      - ``answer``    – the natural, well-phrased answer (or NOT_FOUND_MESSAGE).
      - ``found``     – False when the answer is not in the knowledge base.
      - ``sources``   – [{"file_id", "filename"}] the caller maps to display names.
      - ``reference`` – the verbatim source Q&A text to attach below the answer.
    """
    client = get_client(api_key)

    input_messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        input_messages.extend(history)
    input_messages.append({"role": "user", "content": message})

    response = client.responses.create(
        model=model or settings.openai_model,
        input=input_messages,
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": settings.file_search_max_results,
            }
        ],
    )

    raw = (response.output_text or "").strip()

    # No answer in the knowledge base → signal not-found to the caller.
    if not raw or NO_ANSWER_TOKEN in raw:
        return NOT_FOUND_MESSAGE, False, [], ""

    # Split the natural answer from the verbatim source reference.
    if REF_DELIM in raw:
        answer, reference = raw.split(REF_DELIM, 1)
        answer = answer.strip()
        reference = reference.strip()
    else:
        answer, reference = raw, ""

    return answer, True, _extract_sources(response), reference
