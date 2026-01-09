"use client";

import * as React from "react";
import clsx from "clsx";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={clsx(
        "glass rounded-2xl shadow-[0_20px_60px_rgba(2,132,199,0.12)]",
        "dark:shadow-[0_20px_60px_rgba(59,130,246,0.12)]",
        "p-4",
        props.className
      )}
    />
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }
) {
  const variant = props.variant ?? "primary";
  return (
    <button
      {...props}
      className={clsx(
        "h-11 px-4 rounded-xl font-semibold transition active:scale-[0.99]",
        variant === "primary"
          ? "bg-sky-600 text-white hover:bg-sky-500"
          : "bg-transparent text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-white/10",
        props.disabled && "opacity-60 pointer-events-none",
        props.className
      )}
    />
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={clsx(
        "h-11 w-full rounded-xl border border-black/10 bg-white/70 px-3 outline-none",
        "focus:ring-4 focus:ring-sky-200 dark:bg-white/5 dark:border-white/10 dark:focus:ring-sky-500/20",
        props.className
      )}
    />
  );
}

export function Chip({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  const cls =
    tone === "green"
      ? "bg-emerald-100 text-emerald-800"
      : tone === "blue"
        ? "bg-sky-100 text-sky-900"
        : tone === "purple"
          ? "bg-violet-100 text-violet-900"
          : tone === "red"
            ? "bg-rose-100 text-rose-900"
            : "bg-slate-100 text-slate-800";
  return <span className={clsx("px-2.5 py-1 rounded-full text-xs font-bold", cls)}>{children}</span>;
}

