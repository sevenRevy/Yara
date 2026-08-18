import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { introSlides } from "../../data/introSlides";
import { IntroCard } from "./IntroCard";
import { IntroScene } from "./IntroScene";
import "./intro.css";

import background from "../../../artifacts/2_Background.png";

export function Intro() {
  const [slideIndex, setSlideIndex] = useState(0);

  const slide = introSlides[slideIndex];
  const isLastSlide = slideIndex === introSlides.length - 1;

  const goNext = () => {
    setSlideIndex((current) =>
      Math.min(current + 1, introSlides.length - 1),
    );
  };

  const skipIntro = () => {
    setSlideIndex(introSlides.length - 1);
  };

  return (
    <main className="intro">
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
              />
            </motion.div>
          </AnimatePresence>
        </section>
      </div>
    </main>
  );
}
