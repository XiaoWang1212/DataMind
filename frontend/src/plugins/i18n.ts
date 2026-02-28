import { createI18n } from "vue-i18n";

import en from "@/locales/en";
import zhTW from "@/locales/zh-TW";

const DEFAULT_LOCALE = "zh-TW";

function resolveLocale() {
  const persistedLocale = localStorage.getItem("locale");
  if (persistedLocale === "zh-TW" || persistedLocale === "en") {
    return persistedLocale;
  }

  const browserLocale = navigator.language;
  return browserLocale.startsWith("zh") ? "zh-TW" : "en";
}

const i18n = createI18n({
  legacy: false,
  locale: resolveLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    en,
    "zh-TW": zhTW,
  },
});

export default i18n;
