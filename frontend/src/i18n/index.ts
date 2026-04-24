import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import pt from "./pt";
import en from "./en";

const stored = (localStorage.getItem("lm-lang") as "pt" | "en" | null) ?? "pt";

i18n.use(initReactI18next).init({
  resources: { pt: { translation: pt }, en: { translation: en } },
  lng: stored,
  fallbackLng: "pt",
  interpolation: { escapeValue: false },
});

export function setLanguage(lng: "pt" | "en") {
  i18n.changeLanguage(lng);
  try { localStorage.setItem("lm-lang", lng); } catch { /* noop */ }
  document.documentElement.lang = lng;
}

document.documentElement.lang = stored;

export default i18n;
