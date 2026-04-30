/**
 * i18next setup with react-i18next (FR-040 — zh-TW default, user-switchable to en).
 * ISO/ASPICE terms (ASIL, CAL, SPFM, LFM, PMHF, etc.) are kept in English in both locales.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enJSON from "./en.json";
import zhTWJSON from "./zh-TW.json";

void i18n.use(initReactI18next).init({
  resources: {
    "zh-TW": { translation: zhTWJSON },
    en: { translation: enJSON },
  },
  lng: "zh-TW",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
  returnNull: false,
});

export default i18n;
