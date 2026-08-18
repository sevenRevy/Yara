export type IntroSlide = {
  id: string;
  title: string;
  accent: string;
  text: string;
  bubble: string;
};

export const introSlides: IntroSlide[] = [
  {
    id: "welcome",
    title: "Bem-vindo",
    accent: "à YARA",
    text: "Seu guia de hotel tropical para respostas rápidas, informações da estadia e exploração fácil.",
    bubble: "Oi! Eu sou a YARA —\nVou ajudar você a\ncomeçar.",
  },
  {
    id: "ask",
    title: "Tire dúvidas",
    accent: "sobre sua estadia",
    text: "Informações do hotel, café da manhã, comodidades, recomendações e políticas.",
    bubble: "Mantenho os detalhes úteis do hotel por perto.",
  },
  {
    id: "sample",
    title: "Veja na prática",
    accent: "",
    text: "Vamos explorar juntos como posso ajudar você a aproveitar ao máximo sua estadia.",
    bubble: "Preparei uma reserva de exemplo para você.",
  },
];
