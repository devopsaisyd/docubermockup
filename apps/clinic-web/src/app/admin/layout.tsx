"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Card } from "@/components/ui";

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href;
  return (
    <Link
      href={href}
      className={[
        "h-11 px-3 rounded-xl font-semibold flex items-center",
        active
          ? "bg-sky-600 text-white"
          : "text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-white/10",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl grid gap-6 md:grid-cols-[260px_1fr]">
        <Card className="p-4 h-fit">
          <div className="text-xs font-black text-sky-700 dark:text-sky-300">LocumMap</div>
          <div className="text-lg font-extrabold mt-1">Admin</div>
          <div className="mt-4 grid gap-2">
            <NavLink href="/admin" label="Overview" />
            <NavLink href="/admin/staff" label="Staff & roles" />
            <NavLink href="/admin/billing" label="Billing & invoices" />
            <NavLink href="/shifts" label="Back to shifts" />
          </div>
        </Card>
        <div>{children}</div>
      </div>
    </div>
  );
}

