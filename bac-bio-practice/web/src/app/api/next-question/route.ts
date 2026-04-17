import { cookies } from "next/headers";
import { getNextQuestion, getNextQuestionGroup } from "@/lib/randomize";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { subject, topic } = body;

    if (!subject || !["I", "II", "III", "mixed"].includes(subject)) {
      return Response.json(
        { error: "Subject must be I, II, III, or mixed" },
        { status: 400 }
      );
    }

    // Get or create session ID from cookies
    const cookieStore = await cookies();
    let sessionId = cookieStore.get("session_id")?.value;

    if (!sessionId) {
      sessionId = crypto.randomUUID();
      cookieStore.set("session_id", sessionId, {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24 * 30, // 30 days
      });
    }

    // For Subiectul II and III, return the full question group (all subpoints)
    if (subject === "II" || subject === "III") {
      const questions = await getNextQuestionGroup(
        subject,
        sessionId,
        topic || null
      );

      if (!questions || questions.length === 0) {
        return Response.json(
          { error: "Nu s-au găsit întrebări pentru acest subiect." },
          { status: 404 }
        );
      }

      return Response.json({ questions, sessionId });
    }

    // For Subiectul I and mixed, pick a single question first
    const question = await getNextQuestion(
      subject,
      sessionId,
      topic || null
    );

    if (!question) {
      return Response.json(
        { error: "Nu s-au găsit întrebări pentru acest subiect." },
        { status: 404 }
      );
    }

    // If mixed picked a II/III question, fetch its full group
    if (subject === "mixed" && (question.subject === "II" || question.subject === "III")) {
      const group = await getNextQuestionGroup(
        question.subject,
        sessionId,
        topic || null
      );
      if (group && group.length > 0) {
        return Response.json({ questions: group, sessionId });
      }
    }

    return Response.json({ questions: [question], sessionId });
  } catch (error) {
    console.error("Error fetching next question:", error);
    return Response.json(
      { error: "Eroare internă la încărcarea întrebării." },
      { status: 500 }
    );
  }
}
