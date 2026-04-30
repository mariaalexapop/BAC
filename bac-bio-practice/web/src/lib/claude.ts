import Groq from "groq-sdk";
import { searchChunks } from "@/lib/rag";

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

const groq = new Groq();

export async function gradeAnswer(
  question: GradeInput,
  userAnswer: string
): Promise<GradeResult> {
  try {
    // Find relevant textbook context using RAG
    const ragQuery = `${question.prompt} ${question.baremAnswer}`;
    const relevantChunks = searchChunks(ragQuery, 2);
    const ragContext = relevantChunks.length > 0
      ? `\nContext din manual:\n${relevantChunks.join("\n---\n")}\n`
      : "";

    const systemPrompt = `Ești un profesor de biologie care corectează lucrări pentru Bacalaureat.
Evaluează răspunsul elevului conform baremului oficial.
Acceptă formulări echivalente și sinonime corecte din punct de vedere științific.
Folosește contextul din manual pentru a verifica corectitudinea răspunsului.
Răspunde ÎNTOTDEAUNA în limba română.
Răspunde STRICT în format JSON, fără alte explicații în afara JSON-ului.`;

    const userPrompt = `Întrebarea: ${question.prompt}

Răspunsul corect din barem: ${question.baremAnswer}
${question.baremNotes ? `Note barem: ${question.baremNotes}` : ""}
Punctaj maxim: ${question.points} puncte
${ragContext}
Răspunsul elevului: ${userAnswer}

Evaluează răspunsul și răspunde în format JSON:
{
  "isCorrect": true/false,
  "pointsAwarded": <număr între 0 și ${question.points}>,
  "explanation": "<explicație scurtă în română, menționând ce a fost corect și ce a lipsit>"
}`;

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.3,
      max_tokens: 512,
    });

    const responseText = completion.choices[0]?.message?.content || "";

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
    console.error("Groq grading error:", error);

    return {
      isCorrect: false,
      pointsAwarded: 0,
      explanation: "AI-ul nu a putut fi contactat. Verifică conexiunea și încearcă din nou.",
    };
  }
}
