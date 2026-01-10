"use client";

import { useEffect, useState } from "react";
import { Card, Chip } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { API_BASE_URL } from "@/lib/config";

type Payment = {
  shift_id: string;
  amount_inr: number;
  status: string;
  provider: string;
  provider_order_id: string | null;
  provider_payment_id: string | null;
  created_at: string;
};

type InvoiceRow = {
  shift_id: string;
  status: string;
  amount_inr: number;
  start_time: string;
  end_time: string;
  invoice_url: string;
};

export default function BillingPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const p = await api<Payment[]>("/billing/clinic/payments");
      const i = await api<InvoiceRow[]>("/billing/clinic/invoices");
      setPayments(p);
      setInvoices(i);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load billing");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const tone = (s: string) =>
    s === "paid" ? "green" : s === "failed" ? "red" : s === "created" ? "blue" : "neutral";

  return (
    <div className="grid gap-6">
      <Card className="p-6">
        <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">Billing</div>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Payments & invoices</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Track payments and download invoices for accounting / GST reconciliation.
        </p>
        {error ? <div className="mt-3 text-sm font-semibold text-rose-600">{error}</div> : null}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold">Payments</div>
            <div className="text-xs text-slate-500">{payments.length}</div>
          </div>
          <div className="mt-4 space-y-3 max-h-[520px] overflow-auto pr-1">
            {payments.map((p) => (
              <div
                key={`${p.shift_id}-${p.provider_order_id}`}
                className="rounded-2xl border border-black/10 bg-white/70 p-4 dark:bg-white/5 dark:border-white/10"
              >
                <div className="flex items-center justify-between">
                  <div className="font-extrabold">₹ {p.amount_inr}</div>
                  <Chip tone={tone(p.status)}>{p.status.toUpperCase()}</Chip>
                </div>
                <div className="mt-1 text-xs text-slate-500">Shift: {p.shift_id}</div>
                <div className="mt-1 text-xs text-slate-500">Order: {p.provider_order_id ?? "-"}</div>
                <div className="mt-1 text-xs text-slate-500">Paid: {p.provider_payment_id ?? "-"}</div>
                <div className="mt-1 text-xs text-slate-500">{new Date(p.created_at).toLocaleString()}</div>
              </div>
            ))}
            {payments.length === 0 ? <div className="text-sm text-slate-500">No payments yet.</div> : null}
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-bold">Invoices</div>
            <div className="text-xs text-slate-500">{invoices.length}</div>
          </div>
          <div className="mt-4 space-y-3 max-h-[520px] overflow-auto pr-1">
            {invoices.map((i) => (
              <a
                key={i.shift_id}
                href={`${API_BASE_URL}${i.invoice_url}`}
                target="_blank"
                rel="noreferrer"
                className="block"
              >
                <div className="rounded-2xl border border-black/10 bg-white/70 p-4 hover:bg-white/90 dark:bg-white/5 dark:border-white/10 dark:hover:bg-white/10">
                  <div className="flex items-center justify-between">
                    <div className="font-extrabold">₹ {i.amount_inr}</div>
                    <Chip tone={tone(i.status)}>{i.status.toUpperCase()}</Chip>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    {new Date(i.start_time).toLocaleString()} → {new Date(i.end_time).toLocaleString()}
                  </div>
                  <div className="mt-1 text-xs font-semibold text-sky-700 dark:text-sky-300">
                    Open invoice (HTML) · PDF available at {i.invoice_url}.pdf
                  </div>
                </div>
              </a>
            ))}
            {invoices.length === 0 ? <div className="text-sm text-slate-500">No invoices yet.</div> : null}
          </div>
        </Card>
      </div>
    </div>
  );
}

