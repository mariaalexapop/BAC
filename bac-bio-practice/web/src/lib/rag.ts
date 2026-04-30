import chunks from "@/data/materie_bio_chunks.json";

interface Chunk {
  title: string;
  content: string;
  keywords: string[];
}

const allChunks: Chunk[] = chunks as Chunk[];

/** Normalize Romanian text: strip diacritics, lowercase */
function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

/** Extract meaningful words (4+ chars) from text */
function extractWords(text: string): string[] {
  return normalize(text)
    .match(/[a-z]{4,}/g) || [];
}

/** Find the most relevant chunks for a given query using keyword overlap scoring */
export function searchChunks(query: string, topK = 2): string[] {
  const queryWords = new Set(extractWords(query));
  if (queryWords.size === 0) return [];

  const queryWordArr = Array.from(queryWords);

  const scored = allChunks.map((chunk) => {
    const chunkWords = new Set(chunk.keywords.map(normalize));
    let overlap = 0;
    for (const word of queryWordArr) {
      if (chunkWords.has(word)) overlap++;
    }
    // Also check content for query words not in keywords
    const normalizedContent = normalize(chunk.content);
    for (const word of queryWordArr) {
      if (!chunkWords.has(word) && normalizedContent.includes(word)) {
        overlap += 0.5;
      }
    }
    return { chunk, score: overlap / queryWordArr.length };
  });

  scored.sort((a, b) => b.score - a.score);

  return scored
    .slice(0, topK)
    .filter((s) => s.score > 0.1)
    .map((s) => s.chunk.content);
}
