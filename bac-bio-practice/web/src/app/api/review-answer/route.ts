import { reviewAnswer } from "@/lib/claude";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      prompt,
      baremAnswer,
      baremNotes,
      points,
      userAnswer,
      originalExplanation,
      originalPoints,
    } = body;

    if (!prompt || !baremAnswer || !userAnswer) {
      return Response.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    const result = await reviewAnswer({
      prompt,
      baremAnswer,
      baremNotes: baremNotes || null,
      points: Number(points),
      userAnswer,
      originalExplanation: originalExplanation || "",
      originalPoints: Number(originalPoints) || 0,
    });

    return Response.json({
      isCorrect: result.isCorrect,
      pointsAwarded: result.pointsAwarded,
      explanation: result.explanation,
      modelAnswer: result.modelAnswer || null,
    });
  } catch (error) {
    console.error("Error reviewing answer:", error);
    return Response.json(
      { error: "Eroare la re-evaluare." },
      { status: 500 }
    );
  }
}
