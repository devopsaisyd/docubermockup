"use client";

import Link from "next/link";
import { Card } from "@/components/ui";

export default function AdminHome() {
  return (
    <div className="grid gap-6">
      <Card className="p-6">
        <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">Clinic Admin</div>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight">Operations</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Manage staff, track payments, and export invoices for accounting.
        </p>
      </Card>
      <div className="grid gap-6 md:grid-cols-2">
        <Link href="/admin/staff">
          <Card className="p-6 hover:bg-white/80 dark:hover:bg-white/10 transition">
            <div className="text-xs font-black text-slate-500">RBAC</div>
            <div className="mt-2 text-xl font-extrabold">Staff & roles</div>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              Invite staff for OTP + map-only access.
            </p>
          </Card>
        </Link>
        <Link href="/admin/billing">
          <Card className="p-6 hover:bg-white/80 dark:hover:bg-white/10 transition">
            <div className="text-xs font-black text-slate-500">FINANCE</div>
            <div className="mt-2 text-xl font-extrabold">Billing & invoices</div>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              View payments, download invoices, and reconcile.
            </p>
          </Card>
        </Link>
      </div>
    </div>
  );
}

