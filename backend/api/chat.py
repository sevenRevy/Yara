from __future__ import annotations

from typing import Any

from backend.data_processing.hotel_rag import HotelRAG


def _stream_turn(
    st_module,
    prompt: str,
    rag: HotelRAG,
    bundle: dict[str, Any],
    services: list[dict[str, Any]],
) -> str:
    st_module.session_state.messages.append({"role": "user", "content": prompt})
    with st_module.chat_message("user", avatar="🧳"):
        st_module.markdown(prompt)
    with st_module.chat_message("assistant", avatar="🌴"):
        placeholder = st_module.empty()
        placeholder.markdown("🌴 Pensando...")
        chunks: list[str] = []
        for chunk in rag.answer_stream(prompt, bundle, services):
            chunks.append(chunk)
            placeholder.markdown("".join(chunks) + "▌")
        reply = "".join(chunks).strip()
        placeholder.markdown(reply)
    st_module.session_state.messages.append({"role": "assistant", "content": reply})
    return reply


def render_chat(
    st_module,
    rag: HotelRAG,
    bundle: dict[str, Any],
    services: list[dict[str, Any]],
) -> None:
    pending_prompt = st_module.session_state.pop("pending_prompt", None)

    for message in st_module.session_state.messages:
        avatar = "🌴" if message["role"] == "assistant" else "🧳"
        with st_module.chat_message(message["role"], avatar=avatar):
            st_module.markdown(message["content"])

    if pending_prompt:
        _stream_turn(st_module, pending_prompt, rag, bundle, services)


def render_chat_input(st_module) -> None:
    prompt = st_module.chat_input("Pergunte sobre sua estadia, serviços ou checkout...")
    if not prompt:
        return

    st_module.session_state.pending_prompt = prompt
    st_module.rerun()
