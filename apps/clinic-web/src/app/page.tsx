import Link from "next/link";
import { Card } from "@/components/ui";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <Card className="p-6">
          <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">LocumMap Chennai (MVP)</div>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight">Clinic dashboard</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-300">
            Post shifts, hire verified specialists, and track live location only during the duty window.
          </p>
          <div className="mt-5 flex gap-3">
            <Link
              href="/login"
              className="h-11 px-4 rounded-xl font-semibold bg-sky-600 text-white hover:bg-sky-500 inline-flex items-center"
            >
              Sign in
            </Link>
            <Link
              href="/shifts"
              className="h-11 px-4 rounded-xl font-semibold bg-white/60 border border-black/10 hover:bg-white/80 inline-flex items-center dark:bg-white/10 dark:border-white/10 dark:hover:bg-white/15"
            >
              Open dashboard
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
