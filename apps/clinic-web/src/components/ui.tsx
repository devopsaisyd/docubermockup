"use client";

import * as React from "react";
import clsx from "clsx";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={clsx(
        "glass rounded-2xl p-4",
        "relative overflow-hidden",
        props.className
      )}
    />
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost" | "danger";
    size?: "sm" | "md";
  }
) {
  const variant = props.variant ?? "primary";
  const size = props.size ?? "md";
  return (
    <button
      {...props}
      className={clsx(
        size === "md" ? "h-11 px-4 rounded-xl" : "h-9 px-3 rounded-lg",
        "font-semibold transition active:scale-[0.99] focus:outline-none focus:ring-4 focus:ring-sky-200 dark:focus:ring-sky-500/20",
        variant === "primary" &&
          "bg-gradient-to-b from-sky-500 to-sky-700 text-white hover:from-sky-400 hover:to-sky-700",
        variant === "secondary" &&
          "bg-white/60 border border-black/10 text-slate-900 hover:bg-white/80 dark:bg-white/10 dark:border-white/10 dark:text-white dark:hover:bg-white/15",
        variant === "ghost" &&
          "bg-transparent text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-white/10",
        variant === "danger" &&
          "bg-gradient-to-b from-rose-500 to-rose-700 text-white hover:from-rose-400 hover:to-rose-700",
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
      ? "bg-emerald-100 text-emerald-800 border-emerald-200"
      : tone === "blue"
        ? "bg-sky-100 text-sky-900 border-sky-200"
        : tone === "purple"
          ? "bg-violet-100 text-violet-900 border-violet-200"
          : tone === "red"
            ? "bg-rose-100 text-rose-900 border-rose-200"
            : "bg-slate-100 text-slate-800 border-slate-200";
  return (
    <span className={clsx("px-2.5 py-1 rounded-full text-[11px] font-extrabold border", cls)}>{children}</span>
  );
}

