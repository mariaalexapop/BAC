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
  modelAnswer?: string;
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
Răspunde STRICT în format JSON, fără alte explicații în afara JSON-ului.
Când răspunsul este incorect sau incomplet, scrie un răspuns model complet — exact ce ar trebui să scrie un elev pentru punctaj maxim, bazat pe barem și pe contextul din manual.`;

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
  "explanation": "<scurt feedback: ce a fost corect și ce a lipsit>",
  "modelAnswer": "<răspunsul complet pe care ar trebui să-l scrie un elev pentru punctaj maxim, formulat ca și cum elevul ar scrie pe foaia de examen>"
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
      modelAnswer: parsed.modelAnswer ? String(parsed.modelAnswer) : undefined,
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

interface ReviewInput {
  prompt: string;
  baremAnswer: string;
  baremNotes: string | null;
  points: number;
  userAnswer: string;
  originalExplanation: string;
  originalPoints: number;
}

export async function reviewAnswer(input: ReviewInput): Promise<GradeResult> {
  try {
    const ragQuery = `${input.prompt} ${input.baremAnswer}`;
    const relevantChunks = searchChunks(ragQuery, 2);
    const ragContext = relevantChunks.length > 0
      ? `\nContext din manual:\n${relevantChunks.join("\n---\n")}\n`
      : "";

    const systemPrompt = `Ești un profesor experimentat de biologie care RE-EVALUEAZĂ o corectare contestată de un elev.
Un alt profesor a corectat răspunsul, dar elevul consideră că nota este greșită.
Analizează cu atenție dacă răspunsul elevului merită puncte, chiar dacă formularea diferă de barem.
Acceptă sinonime, formulări echivalente și orice răspuns corect din punct de vedere științific.
Folosește contextul din manual pentru a verifica.
Fii drept și obiectiv — dacă evaluarea inițială a fost corectă, menține-o.
Răspunde ÎNTOTDEAUNA în limba română.
Răspunde STRICT în format JSON.`;

    const userPrompt = `Întrebarea: ${input.prompt}

Răspunsul corect din barem: ${input.baremAnswer}
${input.baremNotes ? `Note barem: ${input.baremNotes}` : ""}
Punctaj maxim: ${input.points} puncte
${ragContext}
Răspunsul elevului: ${input.userAnswer}

Evaluarea inițială: ${input.originalPoints}/${input.points} puncte
Explicația inițială: ${input.originalExplanation}

Elevul contestă această evaluare. Re-evaluează cu atenție și răspunde în format JSON:
{
  "isCorrect": true/false,
  "pointsAwarded": <număr între 0 și ${input.points}>,
  "explanation": "<explicație detaliată: de ce ai menținut sau schimbat nota, ce este corect/greșit în răspunsul elevului>",
  "modelAnswer": "<răspunsul complet pentru punctaj maxim>"
}`;

    const completion = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.2,
      max_tokens: 768,
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
      modelAnswer: parsed.modelAnswer ? String(parsed.modelAnswer) : undefined,
    };
  } catch (error) {
    console.error("Groq review error:", error);
    return {
      isCorrect: false,
      pointsAwarded: 0,
      explanation: "AI-ul nu a putut fi contactat pentru re-evaluare.",
    };
  }
}
