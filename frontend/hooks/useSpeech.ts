"use client";
import { useCallback, useEffect, useRef, useState } from "react";

type SpeechHook = {
  supported: boolean;
  listening: boolean;
  transcript: string;
  interim: string;
  start: () => void;
  stop: () => void;
  speak: (text: string, lang?: string) => void;
  speaking: boolean;
  error: string | null;
};

export function useSpeech(lang: string = "en-IN"): SpeechHook {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interim, setInterim] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recogRef = useRef<any>(null);

  const supported = typeof window !== "undefined" && (!!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition || !!window.speechSynthesis);

  const start = useCallback(() => {
    if (typeof window === "undefined") return;
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setError("SpeechRecognition not supported in this browser");
      return;
    }
    if (recogRef.current) {
      try { recogRef.current.stop(); } catch {}
    }
    const rec = new SR();
    rec.lang = langMap(lang);
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    recogRef.current = rec;
    setError(null);
    setTranscript("");
    setInterim("");
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.onerror = (e: any) => { setError(e.error || "speech error"); setListening(false); };
    rec.onresult = (e: any) => {
      let finalT = "";
      let inter = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalT += res[0].transcript;
        else inter += res[0].transcript;
      }
      if (finalT) setTranscript((p) => (p ? p + " " : "") + finalT.trim());
      setInterim(inter);
    };
    try { rec.start(); } catch (e: any) { setError(e.message); }
  }, [lang]);

  const stop = useCallback(() => {
    if (recogRef.current) {
      try { recogRef.current.stop(); } catch {}
      setListening(false);
    }
  }, []);

  const speak = useCallback((text: string, l?: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = langMap(l || lang);
    u.rate = 1.0;
    u.pitch = 1.0;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  }, [lang]);

  useEffect(() => {
    return () => {
      if (recogRef.current) try { recogRef.current.stop(); } catch {}
      if (typeof window !== "undefined" && window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  return { supported, listening, transcript, interim, start, stop, speak, speaking, error };
}

function langMap(lang: string): string {
  const m: Record<string, string> = {
    en: "en-IN", hi: "hi-IN", ta: "ta-IN", te: "te-IN", kn: "kn-IN",
    "en-IN": "en-IN", "hi-IN": "hi-IN", "ta-IN": "ta-IN", "te-IN": "te-IN", "kn-IN": "kn-IN",
  };
  return m[lang] || "en-IN";
}
