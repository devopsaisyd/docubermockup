"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Button, Chip, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { clearToken } from "@/lib/auth";
import { GOOGLE_MAPS_KEY } from "@/lib/config";

type Shift = {
  id: string;
  specialty: string;
  start_time: string;
  end_time: string;
  pay_amount_inr: number;
  address: string;
  lat: number;
  lng: number;
  status: string;
  assignment_id?: string | null;
  doctor_name?: string | null;
};

async function geocode(address: string): Promise<{ lat: number; lng: number } | null> {
  if (!GOOGLE_MAPS_KEY) return null;
  const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(
    address + ", Chennai"
  )}&key=${encodeURIComponent(GOOGLE_MAPS_KEY)}`;
  const res = await fetch(url);
  const data = await res.json();
  const loc = data?.results?.[0]?.geometry?.location;
  if (!loc) return null;
  return { lat: loc.lat, lng: loc.lng };
}

export default function ShiftsPage() {
  const router = useRouter();
  const [items, setItems] = useState<Shift[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  // create form
  const [specialty, setSpecialty] = useState("dentist_general");
  const [start, setStart] = useState(() => new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString().slice(0, 16));
  const [end, setEnd] = useState(() => new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString().slice(0, 16));
  const [pay, setPay] = useState("3500");
  const [address, setAddress] = useState("T. Nagar, Chennai");
  const [lat, setLat] = useState<string>("13.0418");
  const [lng, setLng] = useState<string>("80.2341");

  const statusChipTone = (s: string) => {
    if (s === "booked") return "blue";
    if (s === "en_route") return "blue";
    if (s === "checked_in") return "green";
    if (s === "completed") return "purple";
    if (s === "paid") return "purple";
    if (s === "canceled" || s === "no_show") return "red";
    return "neutral";
  };

  async function load() {
    setError(null);
    try {
      // If no clinic profile, go to onboarding
      await api("/clinics/me");
      const res = await api<Shift[]>("/shifts");
      setItems(res);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        router.replace("/onboarding");
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/login");
        return;
      }
      setError(e instanceof ApiError ? e.message : "Failed to load shifts");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function signOut() {
    clearToken();
    router.replace("/login");
  }

  async function fillFromGeocode() {
    setCreating(true);
    setError(null);
    try {
      const r = await geocode(address);
      if (!r) throw new Error("Geocoding unavailable. Set lat/lng manually.");
      setLat(String(r.lat));
      setLng(String(r.lng));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Geocoding failed");
    } finally {
      setCreating(false);
    }
  }

  async function createShift() {
    setCreating(true);
    setError(null);
    try {
      await api("/shifts", {
        method: "POST",
        body: JSON.stringify({
          specialty,
          start_time: new Date(start).toISOString(),
          end_time: new Date(end).toISOString(),
          pay_amount_inr: Number(pay),
          address,
          lat: Number(lat),
          lng: Number(lng),
          notes: "MVP",
          auto_replace: false,
        }),
      });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create shift");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">LocumMap Chennai</div>
            <h1 className="text-3xl font-extrabold tracking-tight">Shifts</h1>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </div>

        {error ? <div className="mt-4 text-sm font-semibold text-rose-600">{error}</div> : null}

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <Card className="p-5">
            <div className="text-sm font-bold">Post a shift</div>
            <div className="mt-4 grid gap-3">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Specialty</label>
              <select
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                className="h-11 rounded-xl border border-black/10 bg-white/70 px-3 dark:bg-white/5 dark:border-white/10"
              >
                <option value="dentist_general">Dentist (General)</option>
                <option value="endodontist">Endodontist</option>
                <option value="anesthetist">Anesthetist</option>
              </select>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Start</label>
                  <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">End</label>
                  <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
                </div>
              </div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Pay (₹)</label>
              <Input value={pay} onChange={(e) => setPay(e.target.value)} inputMode="numeric" />
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Address</label>
              <Input value={address} onChange={(e) => setAddress(e.target.value)} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Lat</label>
                  <Input value={lat} onChange={(e) => setLat(e.target.value)} inputMode="decimal" />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Lng</label>
                  <Input value={lng} onChange={(e) => setLng(e.target.value)} inputMode="decimal" />
                </div>
              </div>
            </div>

            <div className="mt-5 flex gap-3">
              <Button variant="ghost" onClick={fillFromGeocode} disabled={creating}>
                Geocode
              </Button>
              <Button onClick={createShift} disabled={creating}>
                Post
              </Button>
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-bold">Your shifts</div>
              <div className="text-xs font-semibold text-slate-500">{items.length} total</div>
            </div>
            <div className="mt-4 space-y-3 max-h-[520px] overflow-auto pr-1">
              {items.map((s) => (
                <Link key={s.id} href={`/shifts/${s.id}`} className="block">
                  <div className="rounded-2xl border border-black/10 bg-white/70 p-4 hover:bg-white/90 dark:bg-white/5 dark:border-white/10 dark:hover:bg-white/10">
                    <div className="flex items-center justify-between">
                      <div className="font-extrabold tracking-tight">{s.specialty.replaceAll("_", " ")}</div>
                      <Chip tone={statusChipTone(s.status)}>{s.status.toUpperCase()}</Chip>
                    </div>
                    <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{s.address}</div>
                    <div className="mt-2 text-xs text-slate-500">
                      {new Date(s.start_time).toLocaleString()} → {new Date(s.end_time).toLocaleString()}
                    </div>
                    {s.doctor_name ? (
                      <div className="mt-2 text-xs font-semibold text-slate-700 dark:text-slate-200">
                        Doctor: {s.doctor_name}
                      </div>
                    ) : null}
                    <div className="mt-2 text-sm font-extrabold">₹ {s.pay_amount_inr}</div>
                  </div>
                </Link>
              ))}
              {items.length === 0 ? (
                <div className="text-sm text-slate-500">No shifts yet. Post one.</div>
              ) : null}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

