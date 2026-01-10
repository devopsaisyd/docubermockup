"use client";

import { useEffect, useState } from "react";
import { Card, Button, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

type Staff = { id: string; phone: string | null; created_at: string };

export default function StaffPage() {
  const [items, setItems] = useState<Staff[]>([]);
  const [phone, setPhone] = useState("9000000010");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setError(null);
    try {
      const res = await api<Staff[]>("/clinics/staff");
      setItems(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load staff");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function invite() {
    setLoading(true);
    setError(null);
    try {
      await api("/clinics/staff/invite", { method: "POST", body: JSON.stringify({ phone }) });
      setPhone("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Invite failed");
    } finally {
      setLoading(false);
    }
  }

  async function remove(id: string) {
    setLoading(true);
    setError(null);
    try {
      await api(`/clinics/staff/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Remove failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6">
      <Card className="p-6">
        <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">Staff</div>
        <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Invite & manage</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-300">
          Staff can log in with OTP and perform OTP + map actions. Admin controls billing.
        </p>
      </Card>

      <Card className="p-6">
        <div className="text-sm font-bold">Invite staff</div>
        <div className="mt-3 flex gap-2">
          <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number" />
          <Button onClick={invite} disabled={loading || phone.trim().length < 8}>
            Invite
          </Button>
        </div>
        {error ? <div className="mt-3 text-sm font-semibold text-rose-600">{error}</div> : null}
      </Card>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div className="text-sm font-bold">Team</div>
          <div className="text-xs text-slate-500">{items.length} members</div>
        </div>
        <div className="mt-4 space-y-3">
          {items.map((s) => (
            <div
              key={s.id}
              className="rounded-2xl border border-black/10 bg-white/70 p-4 dark:bg-white/5 dark:border-white/10 flex items-center justify-between"
            >
              <div>
                <div className="font-extrabold">{s.phone ?? s.id}</div>
                <div className="text-xs text-slate-500">Added: {new Date(s.created_at).toLocaleString()}</div>
              </div>
              <Button variant="ghost" onClick={() => remove(s.id)} disabled={loading}>
                Remove
              </Button>
            </div>
          ))}
          {items.length === 0 ? <div className="text-sm text-slate-500">No staff yet.</div> : null}
        </div>
      </Card>
    </div>
  );
}

