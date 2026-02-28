export interface LandingPrompt {
  id: string;
  textKey: string;
  positionClass: string;
  icon?: string;
}

export interface LandingContent {
  titleKey: string;
  subtitleKey: string;
  loginTextKey: string;
  uploadTextKey: string;
  prompts: LandingPrompt[];
}

export const landingContent: LandingContent = {
  titleKey: "landing.title",
  subtitleKey: "landing.subtitle",
  loginTextKey: "landing.login",
  uploadTextKey: "landing.upload",
  prompts: [
    {
      id: "prompt-1",
      textKey: "landing.prompts.first",
      positionClass: "prompt-pill--left-top",
      icon: "mdi-waveform",
    },
    {
      id: "prompt-2",
      textKey: "landing.prompts.second",
      positionClass: "prompt-pill--right",
      icon: "mdi-waveform",
    },
    {
      id: "prompt-3",
      textKey: "landing.prompts.third",
      positionClass: "prompt-pill--left-bottom",
      icon: "mdi-waveform",
    },
  ],
};
