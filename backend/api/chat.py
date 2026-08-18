from __future__ import annotations

from typing import Any


def _find_service(services: list[dict[str, Any]], needle: str) -> dict[str, Any] | None:
    normalized_needle = needle.lower()

    for service in services:
        if normalized_needle in str(service["name"]).lower():
            return service

    return None


def build_structured_reply(question: str, bundle: dict[str, Any], services: list[dict[str, Any]]) -> str:
    normalized = question.lower()

    if any(token in normalized for token in {"quarto", "room", "reserva", "hospede"}):
        return (
            f"Voce esta na reserva {bundle['reservation_id']}, hospede {bundle['guest']}, "
            f"no quarto {bundle['room_id']} ({bundle['room_type']}). "
            f"Check-in em {bundle['check_in']} e check-out em {bundle['check_out']}."
        )

    if "piscina" in normalized:
        service = _find_service(services, "piscina")
        if service is not None:
            return (
                f"A {service['name'].lower()} está incluída nesta reserva. "
                f"{service['description']}."
            )
        return "A piscina está disponível para a sua estadia."

    if "cafe" in normalized or "breakfast" in normalized:
        service = _find_service(services, "cafe")
        if service is not None:
            return (
                f"O {service['name'].lower()} está incluído nesta reserva. "
                f"{service['description']}."
            )
        return (
            "O cafe da manha esta incluido nesta reserva. "
            "A camada de politicas em PDF entra na proxima etapa para responder horarios e regras."
        )

    if "frigobar" in normalized or "minibar" in normalized:
        return (
            "Sim, o quarto tem frigobar. "
            f"O quarto {bundle['room_id']} foi cadastrado com essa comodidade."
        )

    if "servico" in normalized or "servicos" in normalized:
        included = [service["name"] for service in services if int(service["included"]) == 1]
        return "Serviços incluídos no momento: " + ", ".join(included) + "."

    if "checkout" in normalized:
        return (
            f"Seu checkout atual esta previsto para {bundle['check_out']}. "
            "Perguntas sobre late checkout vao usar o RAG textual na proxima fase."
        )

    return (
        "Estou lendo os dados estruturados da reserva agora. "
        "Se quiser, pergunte sobre quarto, cafe da manha, frigobar, servicos ou checkout."
    )


def _append_turn(
    st_module,
    prompt: str,
    bundle: dict[str, Any],
    services: list[dict[str, Any]],
) -> str:
    st_module.session_state.messages.append({"role": "user", "content": prompt})
    reply = build_structured_reply(prompt, bundle, services)
    st_module.session_state.messages.append({"role": "assistant", "content": reply})
    return reply


def render_chat(st_module, bundle: dict[str, Any], services: list[dict[str, Any]]) -> None:
    pending_prompt = st_module.session_state.pop("pending_prompt", None)
    if pending_prompt:
        _append_turn(st_module, pending_prompt, bundle, services)

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

    reply = build_structured_reply(prompt, bundle, services)
    st_module.session_state.messages.append({"role": "assistant", "content": reply})
    with st_module.chat_message("assistant", avatar="🌴"):
        st_module.markdown(reply)
