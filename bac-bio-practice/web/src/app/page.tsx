import Link from "next/link";

const subjects = [
  {
    id: "I",
    label: "Subiectul I",
    description: "Întrebări cu răspuns scurt, adevărat/fals, completare",
    icon: "🧬",
  },
  {
    id: "II",
    label: "Subiectul II",
    description: "Întrebări structurate cu context și imagini",
    icon: "🔬",
  },
  {
    id: "III",
    label: "Subiectul III",
    description: "Întrebări de tip eseu și răspuns elaborat",
    icon: "🧪",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-gradient-to-b from-teal-50 to-white dark:from-gray-900 dark:to-gray-950 font-sans px-4">
      <main className="flex flex-1 w-full max-w-2xl flex-col items-center justify-center py-16 gap-10">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="text-5xl mb-2">🧬</div>
          <h1 className="text-4xl sm:text-5xl font-bold text-teal-800 dark:text-teal-300 tracking-tight">
            Practică BAC Biologie
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-md mx-auto leading-relaxed">
            Pregătește-te pentru examenul de Bacalaureat la Biologie cu
            întrebări din subiecte oficiale, corectate cu ajutorul AI.
          </p>
        </div>

        {/* Subject buttons */}
        <div className="w-full grid gap-4">
          {subjects.map((subject) => (
            <Link
              key={subject.id}
              href={`/practice/${subject.id}`}
              className="group flex items-center gap-4 p-6 rounded-2xl bg-white dark:bg-gray-800 border-2 border-teal-100 dark:border-gray-700 shadow-sm hover:shadow-lg hover:border-teal-400 dark:hover:border-teal-500 transition-all duration-200"
            >
              <span className="text-3xl">{subject.icon}</span>
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 group-hover:text-teal-700 dark:group-hover:text-teal-400 transition-colors">
                  {subject.label}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {subject.description}
                </p>
              </div>
              <svg
                className="w-5 h-5 text-gray-400 group-hover:text-teal-500 transition-colors"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </Link>
          ))}
        </div>

        {/* Mixed practice button */}
        <Link
          href="/practice/mixed"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-teal-600 hover:bg-teal-700 text-white font-medium text-sm transition-colors shadow-md hover:shadow-lg"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Practică mixtă
        </Link>

        {/* Footer info */}
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
          Întrebări din subiecte oficiale de Bacalaureat. Corectare automată
          conform baremului.
        </p>
      </main>
    </div>
  );
}
