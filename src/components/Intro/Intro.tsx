import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { introSlides } from "../../data/introSlides";
import { IntroCard } from "./IntroCard";
import { IntroScene } from "./IntroScene";
import {
  DEFAULT_DEMO_SCENARIO_ID,
  DEFAULT_STREAMLIT_URL,
} from "./demo";
import "./intro.css";

import background from "../../../artifacts/2_Background.png";

const INTRO_AUDIO_TRACKS = [
  "/audio/Bossa Nova Days.wav",
  "/audio/CastlesMadeOutOfSand.wav",
  "/audio/Shrimp SambaLOOPED.wav",
];

export function Intro() {
  const [slideIndex, setSlideIndex] = useState(0);
  const [audioTrackIndex, setAudioTrackIndex] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioStartedRef = useRef(false);

  const slide = introSlides[slideIndex];
  const isLastSlide = slideIndex === introSlides.length - 1;
  const streamlitUrl = import.meta.env.VITE_STREAMLIT_URL ?? DEFAULT_STREAMLIT_URL;
  const fallbackScenarioId = import.meta.env.VITE_DEMO_SCENARIO_ID ?? DEFAULT_DEMO_SCENARIO_ID;
  const demoScenarioId = slide.demoScenarioId ?? fallbackScenarioId;

  useEffect(() => {
    const audio = audioRef.current;

    if (!audio || !audioStartedRef.current) {
      return;
    }

    void audio.play().catch(() => undefined);
  }, [audioTrackIndex]);

  const playIntroAudio = () => {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    audioStartedRef.current = true;
    audio.volume = 0.28;
    void audio.play().catch(() => undefined);
  };

  const goNext = () => {
    playIntroAudio();
    setSlideIndex((current) =>
      Math.min(current + 1, introSlides.length - 1),
    );
  };

  const skipIntro = () => {
    playIntroAudio();
    setSlideIndex(introSlides.length - 1);
  };

  const startDemo = () => {
    playIntroAudio();
    const targetUrl = new URL(streamlitUrl);
    targetUrl.searchParams.set("scenario", demoScenarioId);
    window.location.assign(targetUrl.toString());
  };

  return (
    <main className="intro">
      <audio
        ref={audioRef}
        src={INTRO_AUDIO_TRACKS[audioTrackIndex]}
        preload="auto"
        onEnded={() =>
          setAudioTrackIndex((current) => (current + 1) % INTRO_AUDIO_TRACKS.length)
        }
      />

      <img className="intro__background" src={background} alt="" aria-hidden="true" />

      <div className="intro__stage">
        <header className="intro__header">
        </header>

        <IntroScene bubble={slide.bubble} />

        <section className="intro__cardLayer" aria-live="polite">
          <AnimatePresence mode="wait">
            <motion.div
              key={slide.id}
              initial={{ opacity: 0, x: 42, rotate: 1 }}
              animate={{ opacity: 1, x: 0, rotate: 0 }}
              exit={{ opacity: 0, x: -28, rotate: -1 }}
              transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
            >
              <IntroCard
                slide={slide}
                currentIndex={slideIndex}
                totalSlides={introSlides.length}
                isLastSlide={isLastSlide}
                onNext={goNext}
                onSkip={skipIntro}
                onStartDemo={startDemo}
              />
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
    </main>
  );
}
