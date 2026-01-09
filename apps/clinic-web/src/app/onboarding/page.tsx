"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Button, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { GOOGLE_MAPS_KEY } from "@/lib/config";

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

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("Lakshmi Dental Clinic");
  const [address, setAddress] = useState("T. Nagar, Chennai");
  const [lat, setLat] = useState<string>("13.0418");
  const [lng, setLng] = useState<string>("80.2341");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        await api("/clinics/me");
        router.replace("/shifts");
      } catch {
        // stay here
      }
    })();
  }, [router]);

  async function fillFromGeocode() {
    setLoading(true);
    setError(null);
    try {
      const r = await geocode(address);
      if (!r) throw new Error("Geocoding unavailable. Set lat/lng manually.");
      setLat(String(r.lat));
      setLng(String(r.lng));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Geocoding failed");
    } finally {
      setLoading(false);
    }
  }

  async function save() {
    setLoading(true);
    setError(null);
    try {
      await api("/clinics/me", {
        method: "POST",
        body: JSON.stringify({
          name,
          address,
          city: "Chennai",
          lat: Number(lat),
          lng: Number(lng),
        }),
      });
      router.replace("/shifts");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-lg">
        <Card className="p-6">
          <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">Onboarding</div>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Create clinic profile</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">Chennai-only MVP boundary enforced.</p>

          <div className="mt-5 grid gap-3">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Clinic name</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Address</label>
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />

            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Lat</label>
                <Input value={lat} onChange={(e) => setLat(e.target.value)} inputMode="decimal" />
              </div>
              <div className="flex-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Lng</label>
                <Input value={lng} onChange={(e) => setLng(e.target.value)} inputMode="decimal" />
              </div>
            </div>

            {error ? <div className="text-sm font-semibold text-rose-600">{error}</div> : null}
          </div>

          <div className="mt-5 flex gap-3">
            <Button variant="ghost" onClick={fillFromGeocode} disabled={loading}>
              Geocode
            </Button>
            <Button onClick={save} disabled={loading}>
              Save
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}

