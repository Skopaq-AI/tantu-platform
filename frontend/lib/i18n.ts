"use client";
import { createContext, useContext } from "react";

export type Lang = "en" | "hi" | "ta" | "te" | "kn";

export const LANG_LABEL: Record<Lang, string> = {
  en: "English",
  hi: "हिन्दी",
  ta: "தமிழ்",
  te: "తెలుగు",
  kn: "ಕನ್ನಡ",
};

export const LANG_NATIVE: Record<Lang, string> = {
  en: "EN",
  hi: "HI",
  ta: "TA",
  te: "TE",
  kn: "KN",
};

type Dict = Record<string, Record<Lang, string>>;

export const dict: Dict = {
  // brand / nav
  app_title: { en: "TANTU", hi: "TANTU", ta: "TANTU", te: "TANTU", kn: "TANTU" },
  mixed_fleet: { en: "Mixed-Fleet", hi: "मिश्रित बेड़ा", ta: "கலப்பு வாகன அணி", te: "మిశ్రమ ఫ్లీట్", kn: "ಮಿಶ್ರ ಫ್ಲೀಟ್" },
  frames_never_leave: {
    en: "Raw frames never leave plant · Dual reasoning",
    hi: "कच्ची छवियां प्लांट से बाहर नहीं जातीं",
    ta: "மூல பிரேம்கள் தொழிற்சாலையை விட்டு வெளியேறாது",
    te: "రా ఫ్రేమ్‌లు ప్లాంట్ నుండి బయటకు వెళ్ళవు",
    kn: "ಕಚ್ಚಾ ಫ್ರೇಮ್‌ಗಳು ಘಟಕದಿಂದ ಹೊರಹೋಗುವುದಿಲ್ಲ",
  },
  operator: { en: "Operator", hi: "ऑपरेटर", ta: "ஆபரேட்டர்", te: "ఆపరేటర్", kn: "ಆಪರೇಟರ್" },
  maintenance: { en: "Maintenance", hi: "रखरखाव", ta: "பராமரிப்பு", te: "నిర్వహణ", kn: "ನಿರ್ವಹಣೆ" },
  plant_head: { en: "Plant Head", hi: "प्लांट हेड", ta: "தொழிற்சாலை தலைவர்", te: "ప్లాంట్ హెడ్", kn: "ಘಟಕ ಮುಖ್ಯಸ್ಥ" },

  // operator — 85dB voice-first
  ack: { en: "ACK", hi: "स्वीकार", ta: "ஏற்றுக்கொள்", te: "ఆమోదించు", kn: "ಒಪ್ಪಿಕೊ" },
  listening: { en: "Listening…", hi: "सुन रहा है…", ta: "கேட்கிறது…", te: "వింటోంది…", kn: "ಆಲಿಸುತ್ತಿದೆ…" },
  tap_to_speak: { en: "Tap to speak", hi: "बोलने के लिए टैप करें", ta: "பேச தொடவும்", te: "మాట్లాడటానికి నొక్కండి", kn: "ಮಾತನಾಡಲು ಟ್ಯಾಪ್ ಮಾಡಿ" },
  one_button_ack: { en: "one-button ack", hi: "एक-बटन स्वीकृति", ta: "ஒரு-பட்டன் ஒப்புதல்", te: "ఒక-బటన్ ఆమోదం", kn: "ಒಂದು-ಬಟನ್ ಒಪ್ಪಿಗೆ" },
  dB_gloved: { en: "85 dB · gloved · 12h shift", hi: "85 dB · दस्ताने · 12 घंटे शिफ्ट", ta: "85 dB · கையுறை · 12 மணி ஷிப்ட்", te: "85 dB · గ్లౌజులు · 12గం షిఫ్ట్", kn: "85 dB · ಕೈಗವಸು · 12ಗಂ ಶಿಫ್ಟ್" },
  live: { en: "LIVE", hi: "लाइव", ta: "நேரலை", te: "లైవ్", kn: "ಲೈವ್" },

  // vernacular — code-switch: technical tokens stay English
  vernacular_pressure: {
    en: "Line 2 pressure high — check valve 3",
    hi: "Line 2 pressure jaasti — valve 3 check karo",
    ta: "Line 2 pressure jaasti — valve 3 paarunga",
    te: "Line 2 pressure ekkuva — valve 3 choodandi",
    kn: "Line 2 pressure jaasti — valve 3 check maadi",
  },
  vernacular_pressure_long: {
    en: "Line 2 — pressure drifting high. Check valve 3 and bypass. 92% confidence.",
    hi: "Line 2 — pressure badh raha hai. Valve 3 aur bypass check karo. 92% confidence.",
    ta: "Line 2 — pressure jaasti aaguthu. Valve 3-ai paarunga. 92% nambikkai.",
    te: "Line 2 — pressure ekkuva avutondi. Valve 3 choodandi. 92% confidence.",
    kn: "Line 2 — pressure jaasti aaguttide. Valve 3 check maadi. 92% confidence.",
  },
  vernacular_vib: {
    en: "Bearing vibration high — schedule check in 2h",
    hi: "Bearing vibration zyada — 2 घंटे में check karo",
    ta: "Bearing vibration jaasti — 2 mani nerathil paarunga",
    te: "Bearing vibration ekkuva — 2 gantalalo choodandi",
    kn: "Bearing vibration jaasti — 2 ganteyalli check maadi",
  },
  vernacular_ack_done: {
    en: "Acknowledged — team notified",
    hi: "स्वीकार किया — टीम को सूचित किया",
    ta: "ஏற்றுக்கொள்ளப்பட்டது — குழுவுக்கு அறிவிப்பு",
    te: "ఆమోదించబడింది — టీమ్‌కు తెలిపాము",
    kn: "ಒಪ್ಪಿಕೊಳ್ಳಲಾಗಿದೆ — ತಂಡಕ್ಕೆ ತಿಳಿಸಲಾಗಿದೆ",
  },

  // plant-head
  walk_reads_title: { en: "Walk-reads / day", hi: "प्रति दिन वॉक-रीड", ta: "நாள் ஒன்றுக்கு நடை வாசிப்பு", te: "రోజుకు వాక్-రీడ్‌లు", kn: "ದಿನಕ್ಕೆ ವಾಕ್-ರೀಡ್‌ಗಳು" },
  pilot_before_after: { en: "Before / After (90-day pilot)", hi: "पहले / बाद में (90 दिन पायलट)", ta: "முன் / பின் (90 நாள் பைலட்)", te: "ముందు / తర్వాత (90-రోజు పైలట్)", kn: "ಮೊದಲು / ನಂತರ (90 ದಿನ ಪೈಲಟ್)" },
  opex_title: { en: "Opex, reversible", hi: "Opex, प्रतिवर्ती", ta: "Opex, மீளக்கூடியது", te: "Opex, రివర్సిబుల్", kn: "Opex, ಹಿಂತಿರುಗಿಸಬಹುದಾದ" },
  ask_copilot: { en: "Ask copilot", hi: "कोपायलट से पूछो", ta: "கோபைலட்டிடம் கேள்", te: "కోపైలట్‌ని అడగండి", kn: "ಕೋಪೈಲಟ್ ಕೇಳಿ" },
  loi_cta: { en: "Sign pilot LOI — Rs 18K / cluster / mo", hi: "पायलट LOI साइन करें — Rs 18K / क्लस्टर / माह", ta: "பைலட் LOI கையெழுத்திடுங்கள் — Rs 18K / கிளஸ்டர் / மாதம்", te: "పైలట్ LOI సంతకం చేయండి — Rs 18K / క్లస్టర్ / నె", kn: "ಪೈಲಟ್ LOI ಸಹಿ ಮಾಡಿ — Rs 18K / ಕ್ಲಸ್ಟರ್ / ತಿಂಗಳು" },
  reversible: { en: "Reversible · 90-day pilot", hi: "प्रतिवर्ती · 90 दिन पायलट", ta: "மீளக்கூடியது · 90 நாள் பைலட்", te: "రివర్సిబుల్ · 90 రోజుల పైలట్", kn: "ಹಿಂತಿರುಗಿಸಬಹುದಾದ · 90 ದಿನ ಪೈಲಟ್" },

  // generic
  view: { en: "View", hi: "देखें", ta: "பார்க்க", te: "చూడండి", kn: "ನೋಡಿ" },
  close: { en: "Close", hi: "बंद करें", ta: "மூடு", te: "మూసివేయి", kn: "ಮುಚ್ಚಿ" },
};

export function t(key: string, lang: Lang): string {
  const entry = dict[key];
  if (!entry) return key;
  return entry[lang] ?? entry.en;
}

// helper for code-switch display (keeps English technical tokens visual distinction)
export function codeSwitch(text: string, _lang: Lang): string {
  return text;
}

export const I18nContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: "en",
  setLang: () => {},
});

export function useI18n() {
  return useContext(I18nContext);
}

// Web Speech lang mapping
export function speechLangCode(lang: Lang): string {
  const m: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", ta: "ta-IN", te: "te-IN", kn: "kn-IN" };
  return m[lang];
}
