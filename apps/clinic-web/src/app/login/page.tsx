"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, Button, Input } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth";

type Step = "phone" | "otp";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("9000000001");
  const [otp, setOtp] = useState("");
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    if (step === "phone") return phone.trim().length >= 8;
    return otp.trim().length >= 4;
  }, [phone, otp, step]);

  async function requestOtp() {
    setLoading(true);
    setError(null);
    try {
      const res = await api<{ ok: boolean; dev_otp?: string | null }>("/auth/otp/request", {
        method: "POST",
        body: JSON.stringify({ phone, role_hint: "clinic_admin" }),
      });
      setDevOtpHint(res.dev_otp ?? null);
      setStep("otp");
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Failed to request OTP");
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp() {
    setLoading(true);
    setError(null);
    try {
      const res = await api<{ access_token: string }>("/auth/otp/verify", {
        method: "POST",
        body: JSON.stringify({ phone, otp, role: "clinic_admin" }),
      });
      setToken(res.access_token);
      router.replace("/shifts");
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Failed to verify OTP");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        <Card className="p-6">
          <div className="text-sm font-semibold text-sky-700 dark:text-sky-300">Sign in</div>
          <h1 className="mt-2 text-2xl font-extrabold tracking-tight">Clinic Admin</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-300">
            OTP is shown only in local demo mode (no SMS).
          </p>

          <div className="mt-5 space-y-3">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300">Phone</label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="e.g. 9000000001" />
            {step === "otp" && (
              <>
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">OTP</label>
                <Input value={otp} onChange={(e) => setOtp(e.target.value)} placeholder="Enter OTP" />
                {devOtpHint ? (
                  <div className="text-xs text-slate-500 dark:text-slate-400">
                    Demo OTP: <span className="font-mono font-bold">{devOtpHint}</span>
                  </div>
                ) : null}
              </>
            )}
            {error ? <div className="text-sm font-semibold text-rose-600">{error}</div> : null}
          </div>

          <div className="mt-5 flex gap-3">
            {step === "phone" ? (
              <Button disabled={!canSubmit || loading} onClick={requestOtp}>
                Get OTP
              </Button>
            ) : (
              <>
                <Button variant="ghost" onClick={() => setStep("phone")} disabled={loading}>
                  Back
                </Button>
                <Button disabled={!canSubmit || loading} onClick={verifyOtp}>
                  Verify
                </Button>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

