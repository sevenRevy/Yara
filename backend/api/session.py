from __future__ import annotations

from dataclasses import dataclass


DEFAULT_SCENARIO_ID = "1001"
WELCOME_MESSAGE = {
    "role": "assistant",
    "content": (
        "Olá! Eu sou a YARA. Posso ajudar com o quarto, o café da manhã, "
        "o frigobar, os serviços e o checkout."
    ),
}


@dataclass(slots=True)
class DemoSession:
    scenario_id: int
    messages: list[dict[str, str]]


def get_scenario_id(st_module) -> int:
    raw_value = st_module.query_params.get("scenario", DEFAULT_SCENARIO_ID)
    if isinstance(raw_value, list):
        raw_value = raw_value[0] if raw_value else DEFAULT_SCENARIO_ID

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return int(DEFAULT_SCENARIO_ID)


def ensure_session_state(st_module, scenario_id: int) -> DemoSession:
    if "scenario_id" not in st_module.session_state or int(st_module.session_state.scenario_id) != int(scenario_id):
        st_module.session_state.scenario_id = scenario_id
        st_module.session_state.messages = [WELCOME_MESSAGE.copy()]
    elif "messages" not in st_module.session_state or not st_module.session_state.messages:
        st_module.session_state.messages = [WELCOME_MESSAGE.copy()]

    return DemoSession(
        scenario_id=int(st_module.session_state.scenario_id),
        messages=st_module.session_state.messages,
    )
