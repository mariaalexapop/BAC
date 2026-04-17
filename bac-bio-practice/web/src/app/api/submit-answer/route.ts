import { prisma } from "@/lib/db";
import { gradeAnswer } from "@/lib/claude";

/** Normalize text for comparison: lowercase, strip diacritics, collapse whitespace, remove punctuation */
function normalizeForComparison(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // strip diacritics
    .toLowerCase()
    .replace(/[.,;:!?'"()[\]{}]/g, "") // strip punctuation
    .replace(/\s+/g, " ")
    .trim();
}

/** Check if two texts are semantically the same after normalization */
function textsMatch(a: string, b: string): boolean {
  return normalizeForComparison(a) === normalizeForComparison(b);
}

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Grouped mode: questionIds[] + single userAnswer (for Subiectul II/III)
    if (body.questionIds && Array.isArray(body.questionIds)) {
      const { questionIds, userAnswer } = body;

      if (!questionIds.length || userAnswer === undefined || userAnswer === null) {
        return Response.json(
          { error: "questionIds and userAnswer are required" },
          { status: 400 }
        );
      }

      const questions = await prisma.question.findMany({
        where: { id: { in: questionIds } },
        orderBy: { number: "asc" },
      });

      if (questions.length === 0) {
        return Response.json(
          { error: "Intrebarile nu au fost gasite." },
          { status: 404 }
        );
      }

      // Combine all prompts and barem answers for a single grading call
      const combinedPrompt = questions
        .map((q) => `${q.number}) ${q.prompt}`)
        .join("\n\n");
      const combinedBarem = questions
        .map((q) => `${q.number}) ${q.baremAnswer}`)
        .join("\n\n");
      const combinedNotes = questions
        .filter((q) => q.baremNotes)
        .map((q) => `${q.number}) ${q.baremNotes}`)
        .join("\n\n");
      const totalPoints = questions.reduce((sum, q) => sum + q.points, 0);

      const gradeResult = await gradeAnswer(
        {
          prompt: combinedPrompt,
          baremAnswer: combinedBarem,
          baremNotes: combinedNotes || null,
          points: totalPoints,
        },
        userAnswer
      );

      // Update attempt for the first question (group representative)
      const recentAttempt = await prisma.attempt.findFirst({
        where: { questionId: questions[0].id },
        orderBy: { shownAt: "desc" },
      });

      if (recentAttempt) {
        await prisma.attempt.update({
          where: { id: recentAttempt.id },
          data: {
            wasCorrect: gradeResult.isCorrect,
            userAnswer: userAnswer,
          },
        });
      }

      return Response.json({
        isCorrect: gradeResult.isCorrect,
        pointsAwarded: gradeResult.pointsAwarded,
        totalPoints,
        baremAnswer: combinedBarem,
        explanation: gradeResult.explanation,
      });
    }

    // Single question mode (Subiectul I / mixed)
    const { questionId, userAnswer } = body;

    if (!questionId || userAnswer === undefined || userAnswer === null) {
      return Response.json(
        { error: "questionId and userAnswer are required" },
        { status: 400 }
      );
    }

    const question = await prisma.question.findUnique({
      where: { id: questionId },
    });

    if (!question) {
      return Response.json(
        { error: "Intrebarea nu a fost gasita." },
        { status: 404 }
      );
    }

    // Deterministic grading for multiple choice — no LLM needed
    // True/false: verdict is deterministic, but correction (when F) needs LLM
    let gradeResult;

    // Detect true/false answers: check questionType OR detect from barem answer + user answer format
    const isTrueFalse = question.questionType === "true_false"
      || (
        /^[AF]$/i.test(question.baremAnswer.trim())
        && /^(fals|adevarat)/i.test(userAnswer.trim())
      );

    console.log("[submit-answer] questionId:", questionId, "questionType:", JSON.stringify(question.questionType), "baremAnswer:", JSON.stringify(question.baremAnswer), "isTrueFalse:", isTrueFalse, "userAnswer:", JSON.stringify(userAnswer.substring(0, 50)));

    if (question.questionType === "multiple_choice") {
      const normalizedUser = userAnswer.trim().toLowerCase();
      const normalizedBarem = question.baremAnswer.trim().toLowerCase();
      const isCorrect = normalizedUser === normalizedBarem;
      gradeResult = {
        isCorrect,
        pointsAwarded: isCorrect ? question.points : 0,
        explanation: isCorrect
          ? "Răspuns corect!"
          : `Răspunsul corect conform baremului: ${question.baremAnswer}.`,
      };
    } else if (isTrueFalse) {
      // True/false scoring per barem rules:
      //   - If barem answer is A (true): 2 pts for correct verdict
      //   - If barem answer is F (false): 2 pts for correct verdict + 2 pts for correct correction = 4 pts total
      // User sends "Adevarat" or "Fals\nCorectie: ...", barem stores "A" or "F"
      const userVerdict = userAnswer.trim().toLowerCase().startsWith("fals") ? "F" : "A";
      const baremVerdict = question.baremAnswer.trim().toUpperCase();
      const verdictCorrect = userVerdict === baremVerdict;
      const verdictPoints = 2;
      const correctionPoints = 2;
      const totalPoints = baremVerdict === "F" ? verdictPoints + correctionPoints : verdictPoints;

      if (!verdictCorrect) {
        // Wrong verdict — 0 points
        gradeResult = {
          isCorrect: false,
          pointsAwarded: 0,
          totalPointsOverride: totalPoints,
          explanation: baremVerdict === "F"
            ? `Afirmația este falsă. Corectare: ${question.falseCorrection || question.baremNotes || ""}`
            : "Afirmația este adevărată.",
        };
      } else if (baremVerdict === "A") {
        // Correctly identified as true — 2/2 points
        gradeResult = {
          isCorrect: true,
          pointsAwarded: verdictPoints,
          totalPointsOverride: totalPoints,
          explanation: "Răspuns corect! Afirmația este adevărată.",
        };
      } else {
        // Correctly identified as false — 2 pts for verdict guaranteed
        // Now grade the correction
        const correctionText = userAnswer.replace(/^fals\s*/i, "").replace(/^corectie:\s*/i, "").trim();
        if (!correctionText) {
          // No correction provided — only verdict points
          gradeResult = {
            isCorrect: false,
            pointsAwarded: verdictPoints,
            totalPointsOverride: totalPoints,
            explanation: `Ai identificat corect că afirmația este falsă (${verdictPoints}p), dar nu ai oferit corectarea. Corectare așteptată: ${question.falseCorrection || ""}`,
          };
        } else if (question.falseCorrection && textsMatch(correctionText, question.falseCorrection)) {
          // Deterministic match — correction matches expected answer
          gradeResult = {
            isCorrect: true,
            pointsAwarded: verdictPoints + correctionPoints,
            totalPointsOverride: totalPoints,
            explanation: "Răspuns corect! Ai identificat corect că afirmația este falsă și ai oferit corectarea corectă.",
          };
        } else {
          // Fall back to LLM for non-obvious corrections
          const correctionGrade = await gradeAnswer(
            {
              prompt: `Afirmația originală: ${question.prompt}\nElevul a identificat corect că este falsă. Evaluează doar corectarea oferită de elev.`,
              baremAnswer: question.falseCorrection || question.baremNotes || "",
              baremNotes: null,
              points: correctionPoints,
            },
            correctionText
          );
          const awarded = verdictPoints + correctionGrade.pointsAwarded;
          gradeResult = {
            isCorrect: awarded === totalPoints,
            pointsAwarded: awarded,
            totalPointsOverride: totalPoints,
            explanation: `Ai identificat corect că afirmația este falsă (${verdictPoints}p). ${correctionGrade.explanation}`,
          };
        }
      }
    } else {
      // Include example answers in grading context when available
      const baremWithExamples = question.exampleAnswer
        ? `${question.baremAnswer}\n\nExemple de răspunsuri corecte:\n${question.exampleAnswer}`
        : question.baremAnswer;
      gradeResult = await gradeAnswer(
        {
          prompt: question.prompt,
          baremAnswer: baremWithExamples,
          baremNotes: question.baremNotes,
          points: question.points,
        },
        userAnswer
      );
    }

    const recentAttempt = await prisma.attempt.findFirst({
      where: { questionId },
      orderBy: { shownAt: "desc" },
    });

    if (recentAttempt) {
      await prisma.attempt.update({
        where: { id: recentAttempt.id },
        data: {
          wasCorrect: gradeResult.isCorrect,
          userAnswer: userAnswer,
        },
      });
    }

    return Response.json({
      isCorrect: gradeResult.isCorrect,
      pointsAwarded: gradeResult.pointsAwarded,
      totalPoints: ("totalPointsOverride" in gradeResult && gradeResult.totalPointsOverride)
        ? gradeResult.totalPointsOverride
        : question.points,
      baremAnswer: question.baremAnswer,
      exampleAnswer: question.exampleAnswer || null,
      explanation: gradeResult.explanation,
    });
  } catch (error) {
    console.error("Error submitting answer:", error);
    return Response.json(
      { error: "Eroare la evaluarea raspunsului." },
      { status: 500 }
    );
  }
}
