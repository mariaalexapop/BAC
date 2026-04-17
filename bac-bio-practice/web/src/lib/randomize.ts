import { prisma } from "./db";

interface QuestionResult {
  id: string;
  subject: string;
  partLabel: string | null;
  number: string;
  prompt: string;
  context: string | null;
  questionType: string;
  points: number;
  imageRefs: string | null;
  testId: string;
  topic: string | null;
  falseCorrection: string | null;
  sourceFile: string | null;
}

// For Subiectul I (and mixed when picking a subject I question): return a single question
export async function getNextQuestion(
  subject: string,
  sessionId: string,
  topic?: string | null
): Promise<QuestionResult | null> {
  const whereClause: Record<string, unknown> = {};
  if (subject !== "mixed") {
    whereClause.subject = subject;
  }
  if (topic) {
    whereClause.topic = topic;
  }

  const allQuestions = await prisma.question.findMany({
    where: whereClause,
    select: { id: true },
  });

  if (allQuestions.length === 0) {
    return null;
  }

  const totalCount = allQuestions.length;
  const skipExclusion = totalCount < 5;
  const excludeCount = skipExclusion
    ? 0
    : Math.min(50, Math.floor(totalCount * 0.3));

  // Get recent attempts to exclude recently shown questions
  const allIds = new Set(allQuestions.map((q) => q.id));
  let recentIds = new Set<string>();

  if (!skipExclusion) {
    // Query recent attempts by session only (avoid huge IN clause)
    const recentAttempts = await prisma.attempt.findMany({
      where: { sessionId },
      orderBy: { shownAt: "desc" },
      take: excludeCount * 2, // fetch extra, then filter to matching questions
      select: { questionId: true },
    });

    const matchingRecent = recentAttempts
      .filter((a) => allIds.has(a.questionId))
      .slice(0, excludeCount);
    recentIds = new Set(matchingRecent.map((a) => a.questionId));
  }

  let candidateIds = allQuestions
    .map((q) => q.id)
    .filter((id) => !recentIds.has(id));

  if (candidateIds.length === 0) {
    candidateIds = allQuestions.map((q) => q.id);
  }

  // For large pools, pick a random subset to query stats for (avoid huge IN clause)
  const MAX_CANDIDATES = 200;
  if (candidateIds.length > MAX_CANDIDATES) {
    // Shuffle and take a subset
    for (let i = candidateIds.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [candidateIds[i], candidateIds[j]] = [candidateIds[j], candidateIds[i]];
    }
    candidateIds = candidateIds.slice(0, MAX_CANDIDATES);
  }

  const candidatesWithStats = await prisma.question.findMany({
    where: { id: { in: candidateIds } },
    select: {
      id: true,
      subject: true,
      partLabel: true,
      number: true,
      prompt: true,
      context: true,
      questionType: true,
      points: true,
      imageRefs: true,
      testId: true,
      topic: true,
      falseCorrection: true,
      exampleAnswer: true,
      test: { select: { sourceFile: true } },
      attempts: {
        where: { sessionId },
        orderBy: { shownAt: "desc" },
        take: 1,
        select: { shownAt: true },
      },
      _count: {
        select: { attempts: true },
      },
    },
  });

  candidatesWithStats.sort((a, b) => {
    const countDiff = a._count.attempts - b._count.attempts;
    if (countDiff !== 0) return countDiff;

    const aLastSeen = a.attempts[0]?.shownAt?.getTime() ?? 0;
    const bLastSeen = b.attempts[0]?.shownAt?.getTime() ?? 0;
    return aLastSeen - bLastSeen;
  });

  const topThirdCount = Math.max(1, Math.ceil(candidatesWithStats.length / 3));
  const topThird = candidatesWithStats.slice(0, topThirdCount);
  const selected = topThird[Math.floor(Math.random() * topThird.length)];

  await prisma.attempt.create({
    data: {
      questionId: selected.id,
      sessionId,
    },
  });

  return {
    id: selected.id,
    subject: selected.subject,
    partLabel: selected.partLabel,
    number: selected.number,
    prompt: selected.prompt,
    context: selected.context,
    questionType: selected.questionType,
    points: selected.points,
    imageRefs: selected.imageRefs,
    testId: selected.testId,
    topic: selected.topic,
    falseCorrection: selected.falseCorrection,
    sourceFile: selected.test?.sourceFile ?? null,
  };
}

// For Subiectul II and III: return all subpoints of a group (same test + subject + partLabel)
export async function getNextQuestionGroup(
  subject: string,
  sessionId: string,
  topic?: string | null
): Promise<QuestionResult[] | null> {
  const whereClause: Record<string, unknown> = { subject };
  if (topic) {
    whereClause.topic = topic;
  }

  // Get all questions and group by testId + partLabel
  const allQuestions = await prisma.question.findMany({
    where: whereClause,
    select: { id: true, testId: true, partLabel: true },
  });

  if (allQuestions.length === 0) {
    return null;
  }

  // Build groups: testId|partLabel -> [questionIds]
  const groups = new Map<string, string[]>();
  for (const q of allQuestions) {
    const key = `${q.testId}|${q.partLabel}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(q.id);
  }

  const groupKeys = Array.from(groups.keys());
  const totalGroups = groupKeys.length;
  const skipExclusion = totalGroups < 3;
  const excludeCount = skipExclusion
    ? 0
    : Math.min(20, Math.floor(totalGroups * 0.3));

  let candidateKeys: string[];

  if (skipExclusion) {
    candidateKeys = groupKeys;
  } else {
    // Get recently shown question IDs for this session
    // Use the first question ID of each group as a representative
    const allGroupFirstIds = groupKeys.map((k) => groups.get(k)![0]);
    const recentAttempts = await prisma.attempt.findMany({
      where: {
        sessionId,
        questionId: { in: allGroupFirstIds },
      },
      orderBy: { shownAt: "desc" },
      take: excludeCount,
      select: { questionId: true },
    });

    const recentFirstIds = new Set(recentAttempts.map((a) => a.questionId));

    candidateKeys = groupKeys.filter(
      (k) => !recentFirstIds.has(groups.get(k)![0])
    );

    if (candidateKeys.length === 0) {
      candidateKeys = groupKeys;
    }
  }

  // Get stats for each candidate group (using first question as representative)
  const representativeIds = candidateKeys.map((k) => groups.get(k)![0]);
  const repsWithStats = await prisma.question.findMany({
    where: { id: { in: representativeIds } },
    select: {
      id: true,
      testId: true,
      partLabel: true,
      attempts: {
        where: { sessionId },
        orderBy: { shownAt: "desc" },
        take: 1,
        select: { shownAt: true },
      },
      _count: {
        select: { attempts: true },
      },
    },
  });

  repsWithStats.sort((a, b) => {
    const countDiff = a._count.attempts - b._count.attempts;
    if (countDiff !== 0) return countDiff;

    const aLastSeen = a.attempts[0]?.shownAt?.getTime() ?? 0;
    const bLastSeen = b.attempts[0]?.shownAt?.getTime() ?? 0;
    return aLastSeen - bLastSeen;
  });

  const topThirdCount = Math.max(1, Math.ceil(repsWithStats.length / 3));
  const topThird = repsWithStats.slice(0, topThirdCount);
  const selectedRep = topThird[Math.floor(Math.random() * topThird.length)];

  const selectedKey = `${selectedRep.testId}|${selectedRep.partLabel}`;
  const selectedIds = groups.get(selectedKey)!;

  // Fetch all questions in this group
  const questions = await prisma.question.findMany({
    where: { id: { in: selectedIds } },
    select: {
      id: true,
      subject: true,
      partLabel: true,
      number: true,
      prompt: true,
      context: true,
      questionType: true,
      points: true,
      imageRefs: true,
      testId: true,
      topic: true,
      falseCorrection: true,
      exampleAnswer: true,
      test: { select: { sourceFile: true } },
    },
    orderBy: { number: "asc" },
  });

  // Record attempt for the first question (as group representative)
  await prisma.attempt.create({
    data: {
      questionId: questions[0].id,
      sessionId,
    },
  });

  return questions.map((q) => ({
    id: q.id,
    subject: q.subject,
    partLabel: q.partLabel,
    number: q.number,
    prompt: q.prompt,
    context: q.context,
    questionType: q.questionType,
    points: q.points,
    imageRefs: q.imageRefs,
    testId: q.testId,
    topic: q.topic,
    falseCorrection: q.falseCorrection,
    sourceFile: q.test?.sourceFile ?? null,
  }));
}
