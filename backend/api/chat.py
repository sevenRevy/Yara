from __future__ import annotations

from typing import Any

from backend.data_processing.hotel_rag import HotelRAG


def _append_turn(
    st_module,
    prompt: str,
    rag: HotelRAG,
    bundle: dict[str, Any],
    services: list[dict[str, Any]],
) -> str:
    st_module.session_state.messages.append({"role": "user", "content": prompt})
    reply = rag.answer(prompt, bundle, services)
    st_module.session_state.messages.append({"role": "assistant", "content": reply})
    return reply


def render_chat(
    st_module,
    rag: HotelRAG,
    bundle: dict[str, Any],
    services: list[dict[str, Any]],
) -> None:
    pending_prompt = st_module.session_state.pop("pending_prompt", None)
    if pending_prompt:
        _append_turn(st_module, pending_prompt, rag, bundle, services)

    for message in st_module.session_state.messages:
        avatar = "🌴" if message["role"] == "assistant" else "🧳"
        with st_module.chat_message(message["role"], avatar=avatar):
            st_module.markdown(message["content"])

    prompt = st_module.chat_input("Pergunte sobre sua estadia, serviços ou checkout...")
    if not prompt:
        return

    st_module.session_state.messages.append({"role": "user", "content": prompt})
    with st_module.chat_message("user", avatar="🧳"):
        st_module.markdown(prompt)

    reply = rag.answer(prompt, bundle, services)
    st_module.session_state.messages.append({"role": "assistant", "content": reply})
    with st_module.chat_message("assistant", avatar="🌴"):
        st_module.markdown(reply)
