import "@testing-library/jest-dom";

// mock fetch
global.fetch = global.fetch || (async () => ({ ok: true, json: async () => [] }) as any);

// mock EventSource
if (typeof (global as any).EventSource === "undefined") {
  (global as any).EventSource = class {
    onopen: any = null;
    onmessage: any = null;
    onerror: any = null;
    close() {}
    addEventListener() {}
    removeEventListener() {}
  };
}

// mock speech
if (typeof window !== "undefined") {
  (window as any).SpeechRecognition = (window as any).SpeechRecognition || undefined;
  (window as any).webkitSpeechRecognition = (window as any).webkitSpeechRecognition || undefined;
}
