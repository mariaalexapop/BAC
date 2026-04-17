interface GradeInput {
  prompt: string;
  baremAnswer: string;
  baremNotes: string | null;
  points: number;
}

interface GradeResult {
  isCorrect: boolean;
  pointsAwarded: number;
  explanation: string;
}

const OLLAMA_URL = process.env.OLLAMA_URL || "http://localhost:11434";
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || "llama3.1";

export async function gradeAnswer(
  question: GradeInput,
  userAnswer: string
): Promise<GradeResult> {
  try {
    const systemPrompt = `Ești un profesor de biologie care corectează lucrări pentru Bacalaureat.
Evaluează răspunsul elevului conform baremului oficial.
Acceptă formulări echivalente și sinonime corecte din punct de vedere științific.
Răspunde ÎNTOTDEAUNA în limba română.
Răspunde STRICT în format JSON, fără alte explicații în afara JSON-ului.`;

    const userPrompt = `Întrebarea: ${question.prompt}

Răspunsul corect din barem: ${question.baremAnswer}
${question.baremNotes ? `Note barem: ${question.baremNotes}` : ""}
Punctaj maxim: ${question.points} puncte

Răspunsul elevului: ${userAnswer}

Evaluează răspunsul și răspunde în format JSON:
{
  "isCorrect": true/false,
  "pointsAwarded": <număr între 0 și ${question.points}>,
  "explanation": "<explicație scurtă în română, menționând ce a fost corect și ce a lipsit>"
}`;

    const res = await fetch(`${OLLAMA_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt },
        ],
        stream: false,
        options: {
          temperature: 0.3,
        },
      }),
    });

    if (!res.ok) {
      throw new Error(`Ollama returned ${res.status}: ${await res.text()}`);
    }

    const data = await res.json();
    const responseText = data.message?.content || "";

    const jsonMatch = responseText.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error("No JSON found in response");
    }

    const parsed = JSON.parse(jsonMatch[0]);
    return {
      isCorrect: Boolean(parsed.isCorrect),
      pointsAwarded: Number(parsed.pointsAwarded) || 0,
      explanation: String(parsed.explanation || ""),
    };
  } catch (error) {
    console.error("Ollama grading error:", error);

    const normalizedUser = userAnswer.trim().toLowerCase();
    const normalizedBarem = question.baremAnswer.trim().toLowerCase();
    const isExactMatch = normalizedUser === normalizedBarem;

    return {
      isCorrect: isExactMatch,
      pointsAwarded: isExactMatch ? question.points : 0,
      explanation: isExactMatch
        ? "Răspunsul tău este corect."
        : `Răspunsul corect conform baremului: ${question.baremAnswer}. Verificarea automată cu AI nu a fost disponibilă.`,
    };
  }
}
