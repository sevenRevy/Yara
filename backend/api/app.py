from __future__ import annotations

import base64
import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import streamlit.components.v1 as components
from streamlit.runtime import get_instance

from backend.api.chat import render_chat
from backend.api.session import ensure_session_state, get_scenario_id
from backend.data_processing.csv_loader import (
    get_reservation,
    load_services,
)
from backend.data_processing.hotel_rag import load_hotel_rag

ARTIFACTS = ROOT / "artifacts"
AUDIO = ROOT / "public" / "audio"
MONTHS_PT = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
AUDIO_TRACKS = (
    "Bossa Nova Days.wav",
    "CastlesMadeOutOfSand.wav",
    "Shrimp SambaLOOPED.wav",
)

ALL_CATEGORIES = [
    {
        "id": "cafe",
        "icon": "☕",
        "title": "Café da manhã",
        "subtitle": "Horários e itens",
        "prompts": [
            "O café da manhã está incluído nesta reserva?",
            "Qual é o horário de funcionamento do café da manhã?",
            "Há opções sem glúten ou sem lactose no café da manhã?",
        ],
    },
    {
        "id": "piscina",
        "icon": "🌊",
        "title": "Piscina & Lazer",
        "subtitle": "Acesso e regras",
        "prompts": [
            "A piscina está disponível para o meu quarto?",
            "Quais são os horários de funcionamento da piscina?",
            "O hotel fornece toalhas para a área da piscina?",
        ],
    },
    {
        "id": "frigobar",
        "icon": "🥤",
        "title": "Frigobar",
        "subtitle": "Itens e consumo",
        "prompts": [
            "Meu quarto possui frigobar?",
            "Como funciona a cobrança dos itens do frigobar?",
            "Posso solicitar reposição de bebidas no frigobar?",
        ],
    },
    {
        "id": "checkout",
        "icon": "🧳",
        "title": "Checkout",
        "subtitle": "Horário e extensão",
        "prompts": [
            "Qual é o horário limite para fazer checkout?",
            "Posso solicitar late checkout para a minha reserva?",
            "Onde posso guardar as malas após o checkout?",
        ],
    },
    {
        "id": "wifi",
        "icon": "📶",
        "title": "Wi-Fi & Conexão",
        "subtitle": "Rede e acesso",
        "prompts": [
            "Qual é a senha do Wi-Fi do hotel?",
            "A conexão Wi-Fi do quarto é rápida para videochamadas?",
            "Como conectar múltiplos dispositivos à rede do hotel?",
        ],
    },
    {
        "id": "estacionamento",
        "icon": "🚗",
        "title": "Estacionamento",
        "subtitle": "Vagas e manobrista",
        "prompts": [
            "O hotel possui estacionamento privativo para hóspedes?",
            "O serviço de estacionamento é gratuito?",
            "Preciso reservar vaga de garagem com antecedência?",
        ],
    },
    {
        "id": "restaurante",
        "icon": "🍽️",
        "title": "Restaurante",
        "subtitle": "Cardápio e reservas",
        "prompts": [
            "Quais são os horários de almoço e jantar do restaurante?",
            "O hotel possui serviço de quarto (room service)?",
            "Preciso fazer reserva prévia para jantar no restaurante?",
        ],
    },
    {
        "id": "limpeza",
        "icon": "🧹",
        "title": "Serviço de Quarto",
        "subtitle": "Arrumação e toalhas",
        "prompts": [
            "Qual é o horário em que é realizada a arrumação do quarto?",
            "Como solicitar toalhas ou travesseiros extras?",
            "Posso agendar um horário específico para a limpeza?",
        ],
    },
]

CATEGORY_COLUMNS = 4
CHAT_HEIGHT_PX = 580


@st.cache_data(show_spinner=False)
def _asset_data_uri(filename: str) -> str:
    asset_path = ARTIFACTS / filename
    if not asset_path.exists():
        return ""
    suffix = asset_path.suffix.lower().lstrip(".") or "png"
    encoded = base64.b64encode(asset_path.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{encoded}"


def _audio_media_urls() -> list[str]:
    media_file_mgr = get_instance().media_file_mgr
    urls: list[str] = []

    for index, filename in enumerate(AUDIO_TRACKS):
        audio_path = AUDIO / filename
        if audio_path.exists():
            urls.append(
                media_file_mgr.add(
                    str(audio_path),
                    "audio/wav",
                    f"yara.audio.{index}",
                    file_name=filename,
                ),
            )

    return urls


def _render_audio_player() -> None:
    tracks = _audio_media_urls()

    if not tracks:
        return

    components.html(
        f"""
        <audio id="yara-streamlit-audio" preload="auto"></audio>
        <script>
        (() => {{
          const tracks = {json.dumps(tracks)};
          const audio = document.getElementById("yara-streamlit-audio");
          let trackIndex = 0;
          let hasStarted = false;

          audio.src = tracks[trackIndex];
          audio.volume = 0.28;

          const playAudio = () => {{
            hasStarted = true;
            audio.play().catch(() => undefined);
          }};

          const advanceTrack = () => {{
            trackIndex = (trackIndex + 1) % tracks.length;
            audio.src = tracks[trackIndex];
            if (hasStarted) {{
              audio.play().catch(() => undefined);
            }}
          }};

          audio.addEventListener("ended", advanceTrack);
          window.parent.document.addEventListener("click", playAudio, {{ once: true }});
        }})();
        </script>
        """,
        height=0,
    )


def _bundle_value(bundle, key: str, default=None):
    try:
        value = bundle[key]
    except (KeyError, IndexError, TypeError):
        return default
    return value if value is not None else default


@st.cache_resource(show_spinner=False)
def _load_rag(_cache_key: tuple[int, int]):
    return load_hotel_rag()


def _rag_cache_key() -> tuple[int, int]:
    raw_dir = ROOT / "data" / "raw"
    pdf_paths = sorted(raw_dir.glob("*.pdf"))
    if not pdf_paths:
        return (0, 0)
    latest_mtime = max(int(path.stat().st_mtime_ns) for path in pdf_paths)
    return (len(pdf_paths), latest_mtime)


def _pretty_date_range(check_in: str, check_out: str) -> str:
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except ValueError:
        return f"{check_in} - {check_out}"

    if start.month == end.month and start.year == end.year:
        return f"{start.day:02d} a {end.day:02d} {MONTHS_PT[start.month - 1]}"

    return (
        f"{start.day:02d} {MONTHS_PT[start.month - 1]} - "
        f"{end.day:02d} {MONTHS_PT[end.month - 1]}"
    )


def _nights_between(check_in: str, check_out: str) -> int | None:
    try:
        start = date.fromisoformat(check_in)
        end = date.fromisoformat(check_out)
    except ValueError:
        return None
    nights = (end - start).days
    return nights if nights > 0 else None


def _time_of_day_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Bom dia"
    if hour < 18:
        return "Boa tarde"
    return "Boa noite"


def _build_css() -> str:
    return """
<style>
:root {
  --bg-main: #faf8f5;
  --text-primary: #1c2a29;
  --text-muted: #5e6c6a;
  --teal-primary: #0e5256;
  --teal-hover: #083c3f;
  --teal-light: rgba(14, 82, 86, 0.08);
  --gold-accent: #c49a45;
  --sage-bg: #e2ebd8;
  --sage-text: #1b4d32;
  --card-bg: rgba(255, 255, 255, 0.92);
  --border-light: rgba(28, 42, 41, 0.08);
  --shadow-soft: 0 12px 32px rgba(14, 82, 86, 0.06);
  --motion-smooth: cubic-bezier(0.2, 0.8, 0.2, 1);
}

/* Hide default Streamlit chrome */
#MainMenu, header, footer {
  visibility: hidden;
}

[data-testid="stSidebar"] {
  display: none;
}

.block-container {
  max-width: 1400px;
  padding: 1rem 2rem 1.25rem;
}

.stApp {
  background: var(--bg-main);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Welcome Banner Header */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--border-light);
  gap: 1rem;
}

.welcome-banner__text {
  flex: 1;
}

.welcome-banner__title {
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--teal-primary);
  letter-spacing: -0.02em;
  margin-bottom: 0.2rem;
}

.welcome-banner__subtitle {
  font-size: 0.95rem;
  color: var(--text-muted);
}

.welcome-banner__logo {
  max-height: 56px;
  width: auto;
  object-fit: contain;
}

/* Stage & Keycard Container */
.character-stage {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  min-height: 580px;
  border-radius: 28px;
  border: 1px solid var(--border-light);
  background: linear-gradient(180deg, #ffffff 0%, #f3efe6 100%);
  box-shadow: var(--shadow-soft);
  overflow: hidden;
  padding-bottom: 1rem;
}

.character-stage__background {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.25;
  pointer-events: none;
}

.character-stage__image {
  position: relative;
  z-index: 1;
  max-height: 340px;
  object-fit: contain;
  filter: drop-shadow(0 10px 20px rgba(0, 0, 0, 0.08));
  margin-bottom: 0.5rem;
}

/* Reservation Key Card */
.hero-reservation {
  position: relative;
  z-index: 2;
  width: 90%;
  max-width: 350px;
  border-radius: 20px;
  border: 1px solid var(--border-light);
  background: var(--card-bg);
  backdrop-filter: blur(16px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transform-origin: center bottom;
  animation: chart-settle 520ms var(--motion-smooth) both;
  transition: transform 240ms var(--motion-smooth), box-shadow 240ms var(--motion-smooth);
}

.hero-reservation:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 30px rgba(14, 82, 86, 0.1);
}

.hero-reservation--feedback {
  animation: chart-feedback 620ms var(--motion-smooth) both;
}

.hero-reservation__rows {
  padding: 0.6rem 1rem;
}

.hero-reservation__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.45rem 0;
  border-bottom: 1px dashed var(--border-light);
  font-size: 0.85rem;
}

.hero-reservation__row:last-child {
  border-bottom: none;
}

.hero-reservation__label {
  color: var(--text-muted);
  font-weight: 500;
}

.hero-reservation__value {
  color: var(--text-primary);
  font-weight: 700;
  text-align: right;
}

.hero-reservation__footer {
  text-align: center;
  padding: 0.6rem 1rem;
  background: var(--sage-bg);
  color: var(--sage-text);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* Category Grid & Buttons */
.section-heading {
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--teal-primary);
  margin-bottom: 0.5rem;
}

div.stButton > button {
  border-radius: 14px !important;
  border: 1px solid var(--border-light) !important;
  background: #ffffff !important;
  color: var(--text-primary) !important;
  font-weight: 600 !important;
  transition:
    transform 180ms var(--motion-smooth),
    border-color 180ms var(--motion-smooth),
    background-color 180ms var(--motion-smooth),
    box-shadow 180ms var(--motion-smooth),
    color 180ms var(--motion-smooth) !important;
  box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
  will-change: transform, box-shadow;
}

div.stButton > button:hover {
  border-color: var(--teal-primary) !important;
  color: var(--teal-primary) !important;
  background: var(--teal-light) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(14, 82, 86, 0.1) !important;
}

div.stButton > button:active {
  transform: translateY(0) scale(0.985);
  box-shadow: 0 3px 8px rgba(14, 82, 86, 0.08) !important;
}

div.stButton > button:focus-visible {
  outline: 3px solid rgba(14, 82, 86, 0.18) !important;
  outline-offset: 2px !important;
}

div.stButton > button[kind="primary"] {
  background: var(--teal-primary) !important;
  border-color: var(--teal-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 12px rgba(14, 82, 86, 0.2) !important;
}

div.stButton > button[kind="primary"]:hover {
  background: var(--teal-hover) !important;
  color: #ffffff !important;
  box-shadow: 0 10px 22px rgba(14, 82, 86, 0.2) !important;
}

/* Prompt Chips Section */
.prompts-container {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: 0.85rem;
  margin: 0.85rem 0 1.25rem 0;
}

.prompts-header {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

@keyframes chart-settle {
  from {
    opacity: 0.9;
    transform: translateY(10px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes chart-feedback {
  0% {
    transform: translateY(6px) scale(0.99);
    box-shadow: 0 6px 18px rgba(14, 82, 86, 0.06);
  }
  52% {
    transform: translateY(-3px) scale(1.01);
    box-shadow: 0 14px 34px rgba(14, 82, 86, 0.12);
  }
  100% {
    transform: translateY(0) scale(1);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-reservation,
  .hero-reservation--feedback,
  div.stButton > button {
    animation: none !important;
    transition: none !important;
  }
}

/* Chat Component Tweaks */
[data-testid="stChatInput"] {
  border-radius: 16px !important;
  border: 1px solid var(--border-light) !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
}

[data-testid="stChatMessage"] {
  background: transparent !important;
  padding: 0.5rem 0 !important;
}

@media (max-width: 900px) {
  .block-container {
    padding: 1rem;
  }
  .welcome-banner {
    flex-direction: column-reverse;
    align-items: flex-start;
  }
  .welcome-banner__logo {
    max-height: 40px;
  }
  .character-stage {
    min-height: 440px;
    margin-bottom: 1.5rem;
  }
  .character-stage__image {
    max-height: 240px;
  }
}
</style>
"""


def _queue_prompt(prompt: str) -> None:
    st.session_state.pending_prompt = prompt
    st.session_state.chart_feedback = True


def _select_category(cat_id: str) -> None:
    st.session_state.active_category_id = cat_id
    st.session_state.chart_feedback = True


def main() -> None:
    st.set_page_config(
        page_title="YARA - Concierge Assistant",
        page_icon="🌴",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_build_css(), unsafe_allow_html=True)
    _render_audio_player()

    scenario_id = get_scenario_id(st)
    session = ensure_session_state(st, scenario_id)
    rag = _load_rag(_rag_cache_key())

    bundle = get_reservation(session.scenario_id)
    if bundle is None:
        st.error(
            f"Reserva {session.scenario_id} não encontrada. Verifique o link e tente novamente."
        )
        return
    services = load_services()

    if "active_category_id" not in st.session_state:
        st.session_state.active_category_id = ALL_CATEGORIES[0]["id"]
    chart_card_class = "hero-reservation"
    if st.session_state.pop("chart_feedback", False):
        chart_card_class += " hero-reservation--feedback"

    guest_name = html.escape(str(bundle["guest"]))
    room_id = html.escape(str(bundle["room_id"]))
    first_name = html.escape(str(bundle["guest"]).split(" ")[0])

    logo_uri = _asset_data_uri("Logo.png")
    logo_img_tag = (
        f'<img class="welcome-banner__logo" src="{logo_uri}" alt="YARA Logo" />'
        if logo_uri
        else ""
    )

    # Welcome Header with Logo
    st.markdown(
        f"""
        <div class="welcome-banner">
            <div class="welcome-banner__text">
                <div class="welcome-banner__title">{_time_of_day_greeting()}, {first_name}! 👋</div>
                <div class="welcome-banner__subtitle">
                    Sou a YARA, sua assistente virtual. Como posso tornar sua estadia ainda melhor hoje?
                </div>
            </div>
            {logo_img_tag}
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_char, col_chat = st.columns([0.9, 1.3], gap="large")

    # Left Column: Character Stage & Glass Key-Card
    with col_char:
        character_uri = _asset_data_uri("YARA.png")
        scene_uri = _asset_data_uri("2_Background.png")
        room_type = html.escape(str(bundle["room_type"]))
        stay_range = _pretty_date_range(str(bundle["check_in"]), str(bundle["check_out"]))
        room_capacity = int(bundle["room_capacity"])
        nights = _nights_between(str(bundle["check_in"]), str(bundle["check_out"]))
        nights_label = f"{nights} noite{'s' if nights != 1 else ''}" if nights else stay_range

        breakfast_included = _bundle_value(bundle, "breakfast_included", True)
        footer_text = "✨ Café da manhã incluso" if breakfast_included else "Café da manhã não incluso"

        st.markdown(
            f"""
            <div class="character-stage">
                <img class="character-stage__background" src="{scene_uri}" alt="" aria-hidden="true" />
                <img class="character-stage__image" src="{character_uri}" alt="YARA Concierge" />
                <div class="{chart_card_class}" aria-label="Detalhes da Reserva">
                    <div class="hero-reservation__rows">
                        <div class="hero-reservation__row">
                            <span class="hero-reservation__label">Hóspede</span>
                            <span class="hero-reservation__value">{guest_name}</span>
                        </div>
                        <div class="hero-reservation__row">
                            <span class="hero-reservation__label">Acomodação</span>
                            <span class="hero-reservation__value">Apto {room_id} · {room_type}</span>
                        </div>
                        <div class="hero-reservation__row">
                            <span class="hero-reservation__label">Período</span>
                            <span class="hero-reservation__value">{stay_range} ({nights_label})</span>
                        </div>
                        <div class="hero-reservation__row">
                            <span class="hero-reservation__label">Capacidade</span>
                            <span class="hero-reservation__value">{room_capacity} pessoas</span>
                        </div>
                    </div>
                    <div class="hero-reservation__footer">
                        {footer_text}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Right Column: Interactive Categories, Prompts & Chat Panel
    with col_chat:
        st.markdown('<div class="section-heading">Assuntos Frequentes</div>', unsafe_allow_html=True)

        # 4-Column Category Grid
        for row_start in range(0, len(ALL_CATEGORIES), CATEGORY_COLUMNS):
            row = ALL_CATEGORIES[row_start : row_start + CATEGORY_COLUMNS]
            cols = st.columns(CATEGORY_COLUMNS)
            for col, cat in zip(cols, row):
                with col:
                    is_active = cat["id"] == st.session_state.active_category_id
                    st.button(
                        f"{cat['icon']} {cat['title']}",
                        key=f"cat_btn_{cat['id']}",
                        use_container_width=True,
                        on_click=_select_category,
                        args=(cat["id"],),
                        type="primary" if is_active else "secondary",
                    )

        selected_cat = next(
            (c for c in ALL_CATEGORIES if c["id"] == st.session_state.active_category_id),
            ALL_CATEGORIES[0],
        )

        # Display category prompt chips directly for frictionless selection
        chip_cols = st.columns(len(selected_cat["prompts"]))
        for idx, (col, prompt_text) in enumerate(zip(chip_cols, selected_cat["prompts"])):
            with col:
                st.button(
                    f"💬 {prompt_text}",
                    key=f"prompt_{selected_cat['id']}_{idx}",
                    use_container_width=True,
                    on_click=_queue_prompt,
                    args=(prompt_text,),
                )

        # Scrollable Chat Container
        with st.container(height=CHAT_HEIGHT_PX, border=False, key="chat_panel"):
            render_chat(st, rag, bundle, services)


if __name__ == "__main__":
    main()
