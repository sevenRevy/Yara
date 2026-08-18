import { motion } from "framer-motion";
import speechBubbleSticker from "../../../artifacts/CreamSpeechBubbleSticker.png";
import yara from "../../../artifacts/YARA.png";

type IntroSceneProps = {
  bubble: string;
};

export function IntroScene({ bubble }: IntroSceneProps) {
  const [beforeYara, afterYara] = bubble.split("YARA");

  return (
    <section className="intro__scene" aria-label="Cena de apresentação da YARA">
      <motion.div
        className="intro__character"
        initial={{ opacity: 0, x: -70, rotate: -2 }}
        animate={{ opacity: 1, x: 0, rotate: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <img src={yara} alt="Assistente de hotel YARA" />

        <motion.div
          className="speechBubble"
          key={bubble}
          initial={{ opacity: 0, scale: 0.74 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{
            duration: 0.38,
            delay: 0.16,
            ease: [0.34, 1.56, 0.64, 1],
          }}
        >
          <img
            className="speechBubble__sticker"
            src={speechBubbleSticker}
            alt=""
            aria-hidden="true"
          />
          <span className="speechBubble__text">
            <span className="speechBubble__line">
              {beforeYara}
              <strong>YARA</strong>
              {afterYara}
            </span>
          </span>
        </motion.div>
      </motion.div>
    </section>
  );
}
