"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { GoogleMap, Marker, useJsApiLoader } from "@react-google-maps/api";
import { io, Socket } from "socket.io-client";

import { Card, Button, Chip, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { API_BASE_URL, GOOGLE_MAPS_KEY } from "@/lib/config";

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
  doctor_user_id?: string | null;
  doctor_name?: string | null;
};

type Candidate = {
  doctor_user_id: string;
  full_name: string;
  eta_minutes: number | null;
  distance_m: number;
  reliability: { on_time_rate: number; avg_rating: number; cancels_count: number; no_show_count: number };
};

type ChatMessage = {
  id: string;
  kind: "text" | "offer" | string;
  sender_role: string;
  message: string | null;
  offer_amount_inr: number | null;
  offer_status: "proposed" | "accepted" | "rejected" | null;
  created_at: string;
};

export default function ShiftDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const shiftId = params.id;

  const [shift, setShift] = useState<Shift | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [live, setLive] = useState<{ lat: number; lng: number; ts: string } | null>(null);
  const [timeline, setTimeline] = useState<{ event_type: string; ts: string; payload: any }[]>([]);
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [chatText, setChatText] = useState("");
  const [offerAmount, setOfferAmount] = useState("3500");
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  const { isLoaded } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: GOOGLE_MAPS_KEY,
  });

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const s = await api<Shift>(`/shifts/${shiftId}`);
      setShift(s);
      if (s.status === "posted") {
        const c = await api<Candidate[]>(`/shifts/${shiftId}/candidates`);
        setCandidates(c);
      }
      if (s.assignment_id) {
        const snap = await api<any>(`/assignments/${s.assignment_id}/live`);
        setTimeline(snap.timeline ?? []);
        const lp = snap.last_ping;
        if (lp) setLive({ lat: lp.lat, lng: lp.lng, ts: lp.ts });
      }
      const msgs = await api<ChatMessage[]>(`/shifts/${shiftId}/chat`);
      setChat(msgs);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.replace("/login");
      else setError(e instanceof ApiError ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shiftId]);

  // Socket.io live updates
  useEffect(() => {
    const token = getToken();
    if (!token) return;

    const socket: Socket = io(API_BASE_URL, {
      path: "/ws/socket.io",
      transports: ["websocket"],
      auth: { token },
    });
    if (shift?.assignment_id) {
      socket.emit("join_assignment", { assignment_id: shift.assignment_id });
      socket.on("assignment_update", (msg: any) => {
        if (msg?.event_type === "location_ping" && msg?.payload?.lat && msg?.payload?.lng) {
          setLive({ lat: msg.payload.lat, lng: msg.payload.lng, ts: msg.payload.ts ?? msg.ts });
        }
        setTimeline((prev) => [...prev, { event_type: msg.event_type, ts: msg.ts, payload: msg.payload }]);
      });
    }
    socket.emit("join_shift", { shift_id: shiftId });
    socket.on("shift_update", (msg: any) => {
      if (msg?.type === "chat_message" && msg?.message) {
        setChat((prev) => [
          ...prev,
          {
            id: msg.message.id,
            kind: msg.message.kind,
            sender_role: msg.message.sender_role,
            message: msg.message.message ?? null,
            offer_amount_inr: msg.message.offer_amount_inr ?? null,
            offer_status: msg.message.offer_status ?? null,
            created_at: msg.message.created_at ?? msg.ts,
          },
        ]);
      }
      if (msg?.type === "offer_update") {
        setChat((prev) =>
          prev.map((m) =>
            m.id === msg.message_id ? { ...m, offer_status: msg.offer_status ?? m.offer_status } : m
          )
        );
      }
    });
    return () => {
      socket.disconnect();
    };
  }, [shift?.assignment_id, shiftId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat.length]);

  const statusTone = useMemo(() => {
    const s = shift?.status;
    if (s === "booked" || s === "en_route") return "blue";
    if (s === "checked_in") return "green";
    if (s === "completed" || s === "paid") return "purple";
    if (s === "canceled" || s === "no_show") return "red";
    return "neutral";
  }, [shift?.status]);

  async function bookDoctor(doctor_user_id: string) {
    setLoading(true);
    setError(null);
    try {
      await api(`/shifts/${shiftId}/book`, { method: "POST", body: JSON.stringify({ doctor_user_id }) });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  async function createPaymentOrder() {
    if (!shift) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api<any>("/payments/create-order", {
        method: "POST",
        body: JSON.stringify({ shift_id: shift.id }),
      });
      setError(
        `Payment order created: ${res.provider_order_id}. (In demo, mark paid via webhook or Razorpay checkout if keys set.)`
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Payment order failed");
    } finally {
      setLoading(false);
    }
  }

  async function createOtp(type: "checkin" | "checkout") {
    if (!shift?.assignment_id) return;
    setLoading(true);
    setError(null);
    setDevOtp(null);
    try {
      const res = await api<any>(`/assignments/${shift.assignment_id}/otp/create?type=${type}`, { method: "POST" });
      setDevOtp(res.dev_otp ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "OTP create failed");
    } finally {
      setLoading(false);
    }
  }

  async function sendChat(kind: "text" | "offer") {
    setLoading(true);
    setError(null);
    try {
      if (kind === "text") {
        const text = chatText.trim();
        if (!text) return;
        const m = await api<ChatMessage>(`/shifts/${shiftId}/chat`, {
          method: "POST",
          body: JSON.stringify({ kind: "text", message: text }),
        });
        setChat((prev) => [...prev, m]);
        setChatText("");
        return;
      }
      const amt = Number(offerAmount);
      if (!Number.isFinite(amt) || amt < 100) throw new Error("Offer amount invalid");
      const m = await api<ChatMessage>(`/shifts/${shiftId}/chat`, {
        method: "POST",
        body: JSON.stringify({ kind: "offer", offer_amount_inr: amt }),
      });
      setChat((prev) => [...prev, m]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  async function respondOffer(messageId: string, action: "accept" | "reject") {
    setLoading(true);
    setError(null);
    try {
      const m = await api<ChatMessage>(`/chat/${messageId}/offer/respond`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      setChat((prev) => prev.map((x) => (x.id === m.id ? m : x)));
      // Refresh shift pay amount after accept
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Offer action failed");
    } finally {
      setLoading(false);
    }
  }

  if (!shift) {
    return (
      <div className="min-h-screen px-6 py-10">
        <div className="mx-auto max-w-5xl">
          <Card className="p-6">Loading…</Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/shifts" className="text-sm font-bold text-sky-700 dark:text-sky-300">
              ← Back
            </Link>
            <div className="mt-2 flex items-center gap-2">
              <h1 className="text-3xl font-extrabold tracking-tight">{shift.specialty.replaceAll("_", " ")}</h1>
              <Chip tone={statusTone}>{shift.status.toUpperCase()}</Chip>
            </div>
            <div className="mt-1 text-slate-600 dark:text-slate-300">{shift.address}</div>
          </div>
          <div className="text-right">
            <div className="text-sm font-extrabold">₹ {shift.pay_amount_inr}</div>
            <div className="text-xs text-slate-500">
              {new Date(shift.start_time).toLocaleString()} → {new Date(shift.end_time).toLocaleString()}
            </div>
          </div>
        </div>

        {error ? <div className="mt-4 text-sm font-semibold text-rose-600">{error}</div> : null}

        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <Card className="p-5 lg:col-span-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-bold">Live shift map</div>
              {shift.doctor_name ? (
                <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">Doctor: {shift.doctor_name}</div>
              ) : null}
            </div>
            <div className="mt-4 overflow-hidden rounded-2xl border border-black/10 dark:border-white/10">
              {isLoaded && GOOGLE_MAPS_KEY ? (
                <GoogleMap
                  mapContainerStyle={{ width: "100%", height: "420px" }}
                  center={live ?? { lat: shift.lat, lng: shift.lng }}
                  zoom={14}
                  options={{
                    disableDefaultUI: true,
                    zoomControl: true,
                    styles: [{ featureType: "poi", stylers: [{ visibility: "off" }] }],
                  }}
                >
                  <Marker position={{ lat: shift.lat, lng: shift.lng }} label="C" />
                  {live ? <Marker position={{ lat: live.lat, lng: live.lng }} label="D" /> : null}
                </GoogleMap>
              ) : (
                <div className="h-[420px] grid place-items-center text-sm text-slate-500">
                  Set `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` to enable maps.
                </div>
              )}
            </div>
            {live ? (
              <div className="mt-3 text-xs text-slate-500">
                Last ping: {new Date(live.ts).toLocaleTimeString()} · {live.lat.toFixed(5)}, {live.lng.toFixed(5)}
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="ghost" onClick={() => createOtp("checkin")} disabled={!shift.assignment_id || loading}>
                Create check-in OTP
              </Button>
              <Button variant="ghost" onClick={() => createOtp("checkout")} disabled={!shift.assignment_id || loading}>
                Create check-out OTP
              </Button>
              <Button onClick={createPaymentOrder} disabled={loading}>
                Create payment order
              </Button>
              <a
                className="h-11 px-4 rounded-xl font-semibold bg-white/60 border border-black/10 hover:bg-white/80 inline-flex items-center dark:bg-white/10 dark:border-white/10 dark:hover:bg-white/15"
                href={`${API_BASE_URL}/invoices/${shift.id}`}
                target="_blank"
                rel="noreferrer"
              >
                Invoice (HTML)
              </a>
            </div>

            {devOtp ? (
              <div className="mt-3 rounded-2xl border border-black/10 bg-white/70 p-4 dark:bg-white/5 dark:border-white/10">
                <div className="text-xs font-bold text-slate-600 dark:text-slate-300">Demo OTP</div>
                <div className="mt-1 text-2xl font-black tracking-widest font-mono">{devOtp}</div>
                <div className="mt-1 text-xs text-slate-500">
                  In production this is sent via SMS / shown only to clinic staff. Never log OTP.
                </div>
              </div>
            ) : null}
          </Card>

          <Card className="p-5">
            <div className="text-sm font-bold">Timeline</div>
            <div className="mt-4 space-y-2 max-h-[520px] overflow-auto pr-1">
              {timeline.map((t, idx) => (
                <div key={idx} className="rounded-xl border border-black/10 bg-white/70 p-3 dark:bg-white/5 dark:border-white/10">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-black">{String(t.event_type).toUpperCase()}</div>
                    <div className="text-[11px] text-slate-500">{new Date(t.ts).toLocaleTimeString()}</div>
                  </div>
                  {t.payload && Object.keys(t.payload).length ? (
                    <pre className="mt-2 text-[11px] text-slate-600 overflow-x-auto dark:text-slate-300">
                      {JSON.stringify(t.payload, null, 2)}
                    </pre>
                  ) : null}
                </div>
              ))}
              {timeline.length === 0 ? <div className="text-sm text-slate-500">No events yet.</div> : null}
            </div>

            {shift.status === "posted" ? (
              <>
                <div className="mt-6 text-sm font-bold">Candidates (ranked by ETA)</div>
                <div className="mt-3 space-y-3">
                  {candidates.map((c) => (
                    <div key={c.doctor_user_id} className="rounded-2xl border border-black/10 bg-white/70 p-4 dark:bg-white/5 dark:border-white/10">
                      <div className="font-extrabold tracking-tight">{c.full_name}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        ETA: {c.eta_minutes ?? "—"} mins · {Math.round(c.distance_m / 1000)} km · On-time{" "}
                        {Math.round(c.reliability.on_time_rate * 100)}%
                      </div>
                      <div className="mt-3">
                        <Button onClick={() => bookDoctor(c.doctor_user_id)} disabled={loading}>
                          Book
                        </Button>
                      </div>
                    </div>
                  ))}
                  {candidates.length === 0 ? (
                    <div className="text-sm text-slate-500">No verified doctors available for this specialty.</div>
                  ) : null}
                </div>
              </>
            ) : null}

            <div className="mt-6 text-sm font-bold">Chat & negotiation</div>
            <div className="mt-3 rounded-2xl border border-black/10 bg-white/70 dark:bg-white/5 dark:border-white/10">
              <div className="max-h-[260px] overflow-auto p-3 space-y-2">
                {chat.map((m) => (
                  <div
                    key={m.id}
                    className={[
                      "rounded-xl p-3 border border-black/10 dark:border-white/10",
                      m.sender_role.startsWith("clinic") ? "bg-sky-50 dark:bg-sky-500/10" : "bg-white/60 dark:bg-white/5",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] font-black text-slate-700 dark:text-slate-200">
                        {m.sender_role.toUpperCase()}
                      </div>
                      <div className="text-[11px] text-slate-500">{new Date(m.created_at).toLocaleTimeString()}</div>
                    </div>
                    {m.kind === "offer" ? (
                      <div className="mt-1">
                        <div className="text-sm font-extrabold">Offer: ₹ {m.offer_amount_inr}</div>
                        <div className="mt-1 flex items-center justify-between">
                          <Chip tone={m.offer_status === "accepted" ? "green" : m.offer_status === "rejected" ? "red" : "blue"}>
                            {(m.offer_status ?? "proposed").toUpperCase()}
                          </Chip>
                          {m.offer_status === "proposed" ? (
                            <div className="flex gap-2">
                              <Button variant="ghost" onClick={() => respondOffer(m.id, "reject")} disabled={loading}>
                                Reject
                              </Button>
                              <Button onClick={() => respondOffer(m.id, "accept")} disabled={loading}>
                                Accept
                              </Button>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : (
                      <div className="mt-1 text-sm text-slate-700 dark:text-slate-200">{m.message}</div>
                    )}
                  </div>
                ))}
                {chat.length === 0 ? <div className="text-sm text-slate-500">No messages yet.</div> : null}
                <div ref={chatEndRef} />
              </div>
              <div className="border-t border-black/10 dark:border-white/10 p-3 space-y-2">
                <div className="flex gap-2">
                  <Input
                    value={chatText}
                    onChange={(e) => setChatText(e.target.value)}
                    placeholder="Message…"
                  />
                  <Button onClick={() => sendChat("text")} disabled={loading}>
                    Send
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Input value={offerAmount} onChange={(e) => setOfferAmount(e.target.value)} inputMode="numeric" />
                  <Button variant="ghost" onClick={() => sendChat("offer")} disabled={loading}>
                    Propose ₹
                  </Button>
                </div>
                <div className="text-[11px] text-slate-500">
                  Accepting an offer updates the shift pay amount for invoicing.
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

