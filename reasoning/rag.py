"""RAG — plant runbooks + tag maps → Qdrant → grounded prompt."""
from dataclasses import dataclass

@dataclass
class Document:
    id: str; text: str; metadata: dict

class RagStore:
    """Stub — in prod: Qdrant client with embeddings (e.g., gemini-embedding-004 or bge-m3)."""
    def __init__(self): self.docs: list[Document]=[]
    def add(self, doc: Document): self.docs.append(doc)
    def search(self, query: str, top_k=3) -> list[Document]:
        # stub: lexical
        return [d for d in self.docs if query.split()[0].lower() in d.text.lower()][:top_k]

PROMPT_REGISTRY = {
  "correlate_v1": "You are TANTU, grounded on tag maps and runbooks. Use only provided context. If uncertain, say 'needs human check'. Summarize in {lang}.",
  "ask_v1": "Answer in {lang}, cite docs, never invent sensor values."
}
