import type { IntroSlide } from "../../data/introSlides";
import emblem from "../../../artifacts/Coral Lotus Water Emblem.png";
import modalArtUp from "../../../artifacts/Modal_art_up.png";

type IntroCardProps = {
  slide: IntroSlide;
  currentIndex: number;
  totalSlides: number;
  isLastSlide: boolean;
  onNext: () => void;
  onSkip: () => void;
  onStartDemo: () => void;
};

function ArrowRightIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" focusable="false">
      <path
        d="M5 12h13m-5-6 6 6-6 6"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.4"
      />
    </svg>
  );
}

function renderAccent(accent: string) {
  const brand = "YARA";

  if (!accent.includes(brand)) {
    return <span className="introCard__accentLine">{accent}</span>;
  }

  const [before, after] = accent.split(brand);

  return (
    <span className="introCard__accentLine">
      {before}
      <span className="introCard__accentBrand">{brand}</span>
      {after}
    </span>
  );
}

export function IntroCard({
  slide,
  currentIndex,
  totalSlides,
  isLastSlide,
  onNext,
  onSkip,
  onStartDemo,
}: IntroCardProps) {
  return (
    <article className="introCard">
      <img
        className="introCard__art introCard__art--up"
        src={modalArtUp}
        alt=""
        aria-hidden="true"
      />

      <div className="introCard__symbol" aria-hidden="true">
        <img src={emblem} alt="" />
      </div>

      <h1>
        {slide.title}
        {renderAccent(slide.accent)}
      </h1>

      <div className="introCard__wave" aria-hidden="true" />

      <p>{slide.text}</p>

      {slide.id === "sample" && (
        <section className="introCard__reservation" aria-label="Resumo da reserva de exemplo">
          <div className="introCard__reservationRows">
            <div className="introCard__reservationRow">
              <span>Hóspede</span>
              <strong>Lucas Mendes</strong>
            </div>
            <div className="introCard__reservationRow">
              <span>Quarto</span>
              <strong>304</strong>
            </div>
            <div className="introCard__reservationRow">
              <span>Categoria</span>
              <strong>Deluxe</strong>
            </div>
            <div className="introCard__reservationRow">
              <span>Datas</span>
              <strong>18 a 21 ago</strong>
            </div>
            <div className="introCard__reservationRow">
              <span>Hóspedes</span>
              <strong>2 pessoas</strong>
            </div>
          </div>

          <div className="introCard__reservationFooter">Café da manhã incluso</div>
        </section>
      )}

      <button
        className="introCard__next"
        type="button"
        onClick={isLastSlide ? onStartDemo : onNext}
      >
        <span>{isLastSlide ? "Iniciar demo" : "Próximo"}</span>
        <ArrowRightIcon />
      </button>

      {!isLastSlide && (
        <button className="introCard__skip" type="button" onClick={onSkip}>
          Pular
        </button>
      )}

      <div className="introCard__dots" aria-label="Progresso da introdução">
        {Array.from({ length: totalSlides }, (_, index) => (
          <span
            key={index}
            className={index === currentIndex ? "active" : ""}
            aria-label={`Slide ${index + 1} de ${totalSlides}`}
          />
        ))}
      </div>
    </article>
  );
}
