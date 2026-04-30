"use client";

import { use, useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";

interface Question {
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

interface GradeResult {
  isCorrect: boolean;
  pointsAwarded: number;
  totalPoints: number;
  baremAnswer: string;
  exampleAnswer?: string | null;
  explanation: string;
  modelAnswer?: string | null;
}

interface TopicInfo {
  topic: string;
  label: string;
  count: number;
}

const subjectLabels: Record<string, string> = {
  I: "Subiectul I",
  II: "Subiectul II",
  III: "Subiectul III",
  mixed: "Practica mixta",
};

/** Parse MCQ options (a/b/c/d) from a question prompt. Returns null if not MCQ. */
function parseMcqOptions(prompt: string): { questionText: string; options: { letter: string; text: string }[] } | null {
  const optionRegex = /^([a-d])\)\s+(.+)$/gm;
  const matches: { letter: string; text: string }[] = [];
  let match;
  while ((match = optionRegex.exec(prompt)) !== null) {
    matches.push({ letter: match[1], text: match[2].trim() });
  }
  if (matches.length < 2) return null;
  const firstOptionIndex = prompt.search(/^[a-d]\)\s+/m);
  const questionText = firstOptionIndex > 0 ? prompt.substring(0, firstOptionIndex).trim() : "";
  return { questionText, options: matches };
}

export default function PracticePage({
  params,
}: {
  params: Promise<{ subject: string }>;
}) {
  const { subject } = use(params);

  const [questions, setQuestions] = useState<Question[]>([]);
  const [userAnswer, setUserAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<GradeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);

  const [reviewing, setReviewing] = useState(false);
  const [prevQuestion, setPrevQuestion] = useState<{
    questions: Question[];
    result: GradeResult;
    userAnswer: string;
  } | null>(null);
  const [showingPrev, setShowingPrev] = useState(false);

  // True/false specific state
  const [tfVerdict, setTfVerdict] = useState<"A" | "F" | null>(null);
  const [tfCorrection, setTfCorrection] = useState("");

  // Topic state
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [topicsLoading, setTopicsLoading] = useState(true);

  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Determine if current question set is grouped (II/III show all subpoints together)
  // For mixed mode, check the actual question's subject
  const actualSubject = questions.length > 0 ? questions[0].subject : subject;
  const isGrouped = actualSubject === "II" || actualSubject === "III";

  // Fetch available topics
  useEffect(() => {
    const fetchTopics = async () => {
      setTopicsLoading(true);
      try {
        const subjectParam =
          subject === "mixed" ? "" : `?subject=${subject}`;
        const res = await fetch(`/api/topics${subjectParam}`);
        if (res.ok) {
          const data = await res.json();
          setTopics(data.topics || []);
        }
      } catch {
        // Topics are optional, don't block on failure
      } finally {
        setTopicsLoading(false);
      }
    };
    fetchTopics();
  }, [subject]);

  const fetchQuestion = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setUserAnswer("");
    setTfVerdict(null);
    setTfCorrection("");

    try {
      const res = await fetch("/api/next-question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          topic: selectedTopic,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Eroare la incarcarea intrebarii");
      }

      const data = await res.json();
      setQuestions(data.questions || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Eroare la incarcarea intrebarii"
      );
    } finally {
      setLoading(false);
    }
  }, [subject, selectedTopic]);

  useEffect(() => {
    fetchQuestion();
  }, [fetchQuestion]);

  // Focus first input when question loads
  useEffect(() => {
    if (questions.length > 0 && !loading && !result) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [questions, loading, result]);

  const handleSubmit = async () => {
    if (questions.length === 0 || !userAnswer.trim() || submitting) return;

    setSubmitting(true);
    try {
      const body =
        isGrouped && questions.length > 1
          ? { questionIds: questions.map((q) => q.id), userAnswer: userAnswer.trim() }
          : { questionId: questions[0].id, userAnswer: userAnswer.trim() };

      const res = await fetch("/api/submit-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Eroare la trimiterea raspunsului");
      }

      const data: GradeResult = await res.json();
      setResult(data);
      setAnsweredCount((c) => c + 1);
      if (data.isCorrect) setCorrectCount((c) => c + 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Eroare la trimiterea raspunsului"
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => {
    if (result && questions.length > 0) {
      setPrevQuestion({ questions, result, userAnswer });
    }
    setShowingPrev(false);
    fetchQuestion();
  };

  const handlePrev = () => {
    if (!prevQuestion) return;
    setQuestions(prevQuestion.questions);
    setResult(prevQuestion.result);
    setUserAnswer(prevQuestion.userAnswer);
    setShowingPrev(true);
  };

  const handleReview = async () => {
    if (!result || !questions.length) return;
    setReviewing(true);
    try {
      const q = questions[0];
      const res = await fetch("/api/review-answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: isGrouped
            ? questions.map((qq) => `${qq.number}) ${qq.prompt}`).join("\n\n")
            : q.prompt,
          baremAnswer: result.baremAnswer,
          baremNotes: q.baremNotes,
          points: result.totalPoints,
          userAnswer,
          originalExplanation: result.explanation,
          originalPoints: result.pointsAwarded,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResult((prev) =>
          prev
            ? {
                ...prev,
                isCorrect: data.isCorrect,
                pointsAwarded: data.pointsAwarded,
                explanation: data.explanation,
                modelAnswer: data.modelAnswer,
              }
            : prev
        );
        if (data.isCorrect && !result.isCorrect) {
          setCorrectCount((c) => c + 1);
        }
      }
    } catch (err) {
      console.error("Review error:", err);
    } finally {
      setReviewing(false);
    }
  };

  const handleTopicChange = (topic: string | null) => {
    setSelectedTopic(topic);
    setAnsweredCount(0);
    setCorrectCount(0);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd+Enter to submit
      if (e.key === "Enter" && !result) {
        const isTextarea = (e.target as HTMLElement)?.tagName === "TEXTAREA";
        if (!isTextarea || e.ctrlKey || e.metaKey) {
          e.preventDefault();
          handleSubmit();
        }
      }
      // Space to go next (only when result is shown and not in input)
      if (e.key === " " && result) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          e.preventDefault();
          handleNext();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const totalTopicQuestions = topics.reduce((sum, t) => sum + t.count, 0);

  // Get shared context (same for all questions in a group)
  const sharedContext = questions.length > 0 ? questions[0].context : null;
  // Get shared images from any question in the group
  const allImageRefs = questions
    .filter((q) => q.imageRefs)
    .flatMap((q) => q.imageRefs!.split(",").map((r) => r.trim()))
    .filter((v, i, a) => a.indexOf(v) === i); // deduplicate

  const totalPoints = questions.reduce((sum, q) => sum + q.points, 0);

  return (
    <div className="flex flex-col flex-1 bg-gradient-to-b from-teal-50 to-white dark:from-gray-900 dark:to-gray-950 font-sans">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            <span className="text-sm font-medium">Acasa</span>
          </Link>

          <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
            {subjectLabels[subject] || subject}
          </h1>

          <div className="text-sm text-gray-500 dark:text-gray-400">
            {answeredCount > 0 && (
              <span>
                {correctCount}/{answeredCount}{" "}
                <span className="text-green-600 dark:text-green-400">
                  corecte
                </span>
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-8">
        {/* Topic selector chips */}
        {!topicsLoading && topics.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
              Capitol
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleTopicChange(null)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                  selectedTopic === null
                    ? "bg-teal-600 text-white shadow-sm"
                    : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                }`}
              >
                Toate capitolele
                <span className="ml-1 opacity-70">({totalTopicQuestions})</span>
              </button>
              {topics.map((t) => (
                <button
                  key={t.topic}
                  onClick={() => handleTopicChange(t.topic)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                    selectedTopic === t.topic
                      ? "bg-teal-600 text-white shadow-sm"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
                  }`}
                >
                  {t.label}
                  <span className="ml-1 opacity-70">({t.count})</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-10 h-10 border-4 border-teal-200 border-t-teal-600 rounded-full animate-spin" />
            <p className="text-gray-500 dark:text-gray-400">
              Se incarca intrebarea...
            </p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <p className="text-gray-600 dark:text-gray-400 text-center">
              {error}
            </p>
            <button
              onClick={fetchQuestion}
              className="px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg transition-colors"
            >
              Incearca din nou
            </button>
          </div>
        )}

        {/* Question(s) */}
        {questions.length > 0 && !loading && !error && (
          <div className="space-y-6">
            {/* Question header */}
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <span className="px-2 py-1 bg-teal-100 dark:bg-teal-900 text-teal-700 dark:text-teal-300 rounded-md font-medium">
                {questions[0].subject}
              </span>
              {questions[0].partLabel && (
                <span className="text-gray-400 font-medium">
                  {questions[0].partLabel}
                </span>
              )}
              {!isGrouped && (
                <span>Nr. {questions[0].number}</span>
              )}
              <span className="ml-auto font-medium">
                {totalPoints}{" "}
                {totalPoints === 1 ? "punct" : "puncte"}
              </span>
            </div>

            {/* Shared context */}
            {sharedContext && (
              <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                {sharedContext.replace(/^[A-D]\.?\s+\d+\s*(?:de\s+)?puncte?\s+/i, "")}
              </div>
            )}

            {/* Shared images */}
            {allImageRefs.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {allImageRefs.map((ref, i) => (
                  <div
                    key={i}
                    className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs text-gray-500"
                  >
                    {ref}
                  </div>
                ))}
              </div>
            )}

            {/* Question block: one card with all subpoints for II/III, single prompt for I */}
            <div className="p-6 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
              {isGrouped && questions.length > 1 ? (
                <div className="space-y-4">
                  {questions.map((q) => {
                    // Strip leading "a) " / "b) " etc. from prompt if it already starts with the letter
                    const stripped = q.prompt.replace(/^[a-d]\)\s*/, "");
                    return (
                      <p key={q.id} className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
                        <span className="font-semibold text-teal-700 dark:text-teal-400">{q.number})</span>{" "}
                        {stripped}
                      </p>
                    );
                  })}
                </div>
              ) : (
                <p className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap">
                  {(() => {
                    // Strip leading "A 4 puncte" / "B 6 puncte" prefix from prompt
                    const raw = questions[0].prompt.replace(/^[A-D]\.?\s+\d+\s*(?:de\s+)?puncte?\s+/i, "");
                    const mcq = parseMcqOptions(raw);
                    return mcq ? mcq.questionText || raw : raw;
                  })()}
                </p>
              )}
            </div>

            {/* Answer input: always one field */}
            <div className="space-y-3">
              {questions[0].questionType === "true_false" && !isGrouped ? (
                <>
                  {/* Radio buttons for Adevarat / Fals */}
                  <div className="space-y-2">
                    <label
                      onClick={() => {
                        if (result) return;
                        setTfVerdict("A");
                        setTfCorrection("");
                        setUserAnswer("Adevarat");
                      }}
                      className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                        tfVerdict === "A"
                          ? "border-teal-500 bg-teal-50 dark:bg-teal-900/30 dark:border-teal-600"
                          : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-teal-300 dark:hover:border-teal-700"
                      } ${result ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
                    >
                      <input
                        type="radio"
                        name="tf-verdict"
                        value="A"
                        checked={tfVerdict === "A"}
                        onChange={() => {}}
                        disabled={!!result}
                        className="w-4 h-4 text-teal-600 border-gray-300 focus:ring-teal-500"
                      />
                      <span className="font-medium text-gray-800 dark:text-gray-200">Adevarat</span>
                    </label>
                    <label
                      onClick={() => {
                        if (result) return;
                        setTfVerdict("F");
                        setUserAnswer(""); // Clear until correction is provided
                        setTimeout(() => inputRef.current?.focus(), 100);
                      }}
                      className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                        tfVerdict === "F"
                          ? "border-teal-500 bg-teal-50 dark:bg-teal-900/30 dark:border-teal-600"
                          : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-teal-300 dark:hover:border-teal-700"
                      } ${result ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
                    >
                      <input
                        type="radio"
                        name="tf-verdict"
                        value="F"
                        checked={tfVerdict === "F"}
                        onChange={() => {}}
                        disabled={!!result}
                        className="w-4 h-4 text-teal-600 border-gray-300 focus:ring-teal-500"
                      />
                      <span className="font-medium text-gray-800 dark:text-gray-200">Fals</span>
                    </label>
                  </div>

                  {/* Correction input when Fals is selected */}
                  {tfVerdict === "F" && !result && (
                    <div className="space-y-2">
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Modifica afirmatia pentru a deveni adevarata (fara a folosi negatia):
                      </p>
                      <textarea
                        ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                        value={tfCorrection}
                        onChange={(e) => {
                          setTfCorrection(e.target.value);
                          setUserAnswer(`Fals\nCorectie: ${e.target.value}`);
                        }}
                        disabled={!!result}
                        placeholder="Scrie afirmatia corectata..."
                        rows={3}
                        className="w-full p-4 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-teal-400 focus:ring-2 focus:ring-teal-100 dark:focus:ring-teal-900 outline-none transition-all resize-y disabled:opacity-60 disabled:cursor-not-allowed"
                      />
                    </div>
                  )}

                  {/* Submit button for true_false */}
                  {tfVerdict === "A" && !result && (
                    <>
                      <button
                        id="submit-btn"
                        onClick={handleSubmit}
                        className="w-full py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl transition-colors shadow-sm"
                      >
                        {submitting ? (
                          <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            Se evalueaza...
                          </span>
                        ) : (
                          "Trimite raspunsul"
                        )}
                      </button>
                    </>
                  )}
                  {tfVerdict === "F" && !result && (
                    <button
                      id="submit-btn"
                      onClick={handleSubmit}
                      disabled={!tfCorrection.trim() || submitting}
                      className="w-full py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors shadow-sm"
                    >
                      {submitting ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Se evalueaza...
                        </span>
                      ) : (
                        "Trimite raspunsul"
                      )}
                    </button>
                  )}
                  {submitting && !tfVerdict && (
                    <div className="flex items-center justify-center py-3 text-gray-500 dark:text-gray-400 gap-2">
                      <span className="w-4 h-4 border-2 border-teal-300 border-t-teal-600 rounded-full animate-spin" />
                      Se evalueaza...
                    </div>
                  )}
                </>
              ) : !isGrouped && parseMcqOptions(questions[0].prompt) ? (
                /* Multiple choice with radio buttons */
                <>
                  <div className="space-y-2">
                    {parseMcqOptions(questions[0].prompt)!.options.map((opt) => (
                      <label
                        key={opt.letter}
                        onClick={() => {
                          if (result) return;
                          setUserAnswer(opt.letter);
                        }}
                        className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                          userAnswer === opt.letter
                            ? "border-teal-500 bg-teal-50 dark:bg-teal-900/30 dark:border-teal-600"
                            : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-teal-300 dark:hover:border-teal-700"
                        } ${result ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
                      >
                        <input
                          type="radio"
                          name="mcq-answer"
                          value={opt.letter}
                          checked={userAnswer === opt.letter}
                          onChange={() => {}}
                          disabled={!!result}
                          className="w-4 h-4 text-teal-600 border-gray-300 focus:ring-teal-500"
                        />
                        <span className="font-semibold text-teal-700 dark:text-teal-400">
                          {opt.letter})
                        </span>
                        <span className="text-gray-800 dark:text-gray-200">{opt.text}</span>
                      </label>
                    ))}
                  </div>
                  {!result && (
                    <button
                      id="submit-btn"
                      onClick={handleSubmit}
                      disabled={!userAnswer.trim() || submitting}
                      className="w-full py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors shadow-sm"
                    >
                      {submitting ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Se evalueaza...
                        </span>
                      ) : (
                        "Trimite raspunsul"
                      )}
                    </button>
                  )}
                </>
              ) : (
                /* Default: textarea for essay, multi_part, short_answer, fill_blank */
                <>
                  <textarea
                    ref={inputRef as React.RefObject<HTMLTextAreaElement>}
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    disabled={!!result}
                    placeholder="Scrie raspunsul tau aici..."
                    rows={isGrouped ? 10 : 6}
                    className="w-full p-4 rounded-xl border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:border-teal-400 focus:ring-2 focus:ring-teal-100 dark:focus:ring-teal-900 outline-none transition-all resize-y disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                  {!result && (
                    <button
                      id="submit-btn"
                      onClick={handleSubmit}
                      disabled={!userAnswer.trim() || submitting}
                      className="w-full py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors shadow-sm"
                    >
                      {submitting ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Se evalueaza...
                        </span>
                      ) : (
                        "Trimite raspunsul"
                      )}
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Result */}
            {result && (
              <div className="space-y-4 animate-in">
                <div
                  className={`p-4 rounded-xl border-2 ${
                    result.isCorrect
                      ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
                      : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div>
                      <p
                        className={`font-semibold ${
                          result.isCorrect
                            ? "text-green-700 dark:text-green-400"
                            : "text-red-700 dark:text-red-400"
                        }`}
                      >
                        {result.isCorrect ? "Corect!" : "Incorect"}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {result.pointsAwarded} / {result.totalPoints} puncte
                      </p>
                    </div>
                  </div>
                </div>

                {/* Example answer — shown first when available */}
                {result.exampleAnswer && (
                  <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl">
                    <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide mb-2">
                      Exemple de raspunsuri corecte
                    </p>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {result.exampleAnswer}
                    </p>
                  </div>
                )}

                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
                  <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-2">
                    Raspuns barem
                  </p>
                  <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                    {result.baremAnswer === "A" ? "Adevarat" : result.baremAnswer === "F" ? "Fals" : result.baremAnswer}
                  </p>
                  {/* Show expected correction for false T/F questions */}
                  {questions[0]?.questionType === "true_false" && questions[0]?.falseCorrection && result.baremAnswer === "F" && (
                    <div className="mt-3 pt-3 border-t border-blue-200 dark:border-blue-700">
                      <p className="text-xs font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-1">
                        Corectie asteptata
                      </p>
                      <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
                        {questions[0].falseCorrection}
                      </p>
                    </div>
                  )}
                </div>

                {result.explanation && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                      Explicatie
                    </p>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {result.explanation}
                    </p>
                  </div>
                )}

                {result.modelAnswer && !result.isCorrect && (
                  <div className="p-4 bg-teal-50 dark:bg-teal-900/30 border border-teal-200 dark:border-teal-700 rounded-xl">
                    <p className="text-xs font-semibold text-teal-600 dark:text-teal-400 uppercase tracking-wide mb-2">
                      Raspuns model pentru punctaj maxim
                    </p>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                      {result.modelAnswer}
                    </p>
                  </div>
                )}

                {!result.isCorrect && (
                  <button
                    onClick={handleReview}
                    disabled={reviewing}
                    className="w-full py-2.5 bg-amber-50 hover:bg-amber-100 dark:bg-amber-900/20 dark:hover:bg-amber-900/40 text-amber-700 dark:text-amber-400 font-medium text-sm rounded-xl transition-colors border border-amber-200 dark:border-amber-700 disabled:opacity-50"
                  >
                    {reviewing ? "Se re-evaluează..." : "Contestă evaluarea"}
                  </button>
                )}

                <div className="flex gap-2">
                  {prevQuestion && !showingPrev && (
                    <button
                      onClick={handlePrev}
                      className="py-3 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 font-medium rounded-xl transition-colors border border-gray-200 dark:border-gray-700"
                    >
                      &larr;
                    </button>
                  )}
                  <button
                    onClick={handleNext}
                    className="flex-1 py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl transition-colors shadow-sm"
                  >
                    {showingPrev ? "Inapoi la intrebarea curenta" : "Urmatoarea intrebare"}
                  </button>
                </div>
                <p className="text-center text-xs text-gray-400 dark:text-gray-500">
                  Apasa <kbd className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">Space</kbd> pentru urmatoarea intrebare
                </p>
              </div>
            )}

            {/* Source file reference */}
            {questions[0]?.sourceFile && (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-right">
                Sursa: {questions[0].sourceFile.replace(/\.pdf$/i, "")}
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
