import { prisma } from "@/lib/db";
import { NextRequest } from "next/server";

const TOPIC_LABELS: Record<string, string> = {
  sistem_nervos: "Sistem nervos",
  analizatori: "Analizatori",
  sistem_endocrin: "Sistem endocrin",
  sistem_osos: "Sistem osos",
  sistem_muscular: "Sistem muscular",
  sistem_digestiv: "Sistem digestiv",
  sistem_circulator: "Sistem circulator",
  sistem_respirator: "Sistem respirator",
  sistem_excretor: "Sistem excretor",
  sistem_reproducator: "Sistem reproducător",
  genetica: "Genetică",
  ecologie_umana: "Ecologie umană",
  alcatuirea_corpului: "Alcătuirea corpului uman",
  mixt: "Mixt",
  altele: "Altele",
};

export async function GET(request: NextRequest) {
  try {
    const subject = request.nextUrl.searchParams.get("subject");

    // Build where clause
    const whereClause: Record<string, unknown> = {
      topic: { not: null },
    };
    if (subject && ["I", "II", "III"].includes(subject)) {
      whereClause.subject = subject;
    }

    // Group by topic and count
    const questions = await prisma.question.groupBy({
      by: ["topic"],
      where: whereClause,
      _count: { id: true },
    });

    // Build result, filtering out topics with 0 questions
    const topics = questions
      .filter((q) => q.topic !== null)
      .map((q) => ({
        topic: q.topic!,
        label: TOPIC_LABELS[q.topic!] || q.topic!,
        count: q._count.id,
      }))
      .sort((a, b) => b.count - a.count);

    return Response.json({ topics });
  } catch (error) {
    console.error("Error fetching topics:", error);
    return Response.json(
      { error: "Eroare la încărcarea topicurilor." },
      { status: 500 }
    );
  }
}
