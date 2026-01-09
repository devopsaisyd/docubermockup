import { StatusBar } from "expo-status-bar";
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import MapView, { Marker } from "react-native-maps";

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const LOCATION_TASK = "locummap-location-task";

type Role = "doctor";

type TokenRes = { access_token: string };
type MeDoctor = {
  id: string;
  full_name: string;
  specialty: "dentist_general" | "endodontist" | "anesthetist";
  reg_no: string;
  verification_status: "pending" | "approved" | "rejected";
};
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
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await AsyncStorage.getItem("locummap_token");
  const headers: any = { "Content-Type": "application/json", ...(init?.headers ?? {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  const text = await res.text();
  const body = text ? safeJson(text) : null;
  if (!res.ok) {
    const msg = (body && typeof body === "object" && (body as any).detail) || `HTTP ${res.status}`;
    throw new Error(String(msg));
  }
  return body as T;
}

function safeJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

TaskManager.defineTask(LOCATION_TASK, async ({ data, error }) => {
  if (error) return;
  const token = await AsyncStorage.getItem("locummap_token");
  const assignmentId = await AsyncStorage.getItem("locummap_active_assignment_id");
  if (!token || !assignmentId) return;
  const loc = (data as any)?.locations?.[0];
  if (!loc) return;
  const payload = {
    ts: new Date(loc.timestamp).toISOString(),
    lat: loc.coords.latitude,
    lng: loc.coords.longitude,
    speed: loc.coords.speed ?? null,
    heading: loc.coords.heading ?? null,
    accuracy: loc.coords.accuracy ?? null,
  };
  try {
    await fetch(`${API_BASE_URL}/assignments/${assignmentId}/location`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    });
  } catch {
    // ignore
  }
});

async function startBackgroundTracking(assignmentId: string) {
  await AsyncStorage.setItem("locummap_active_assignment_id", assignmentId);
  const hasStarted = await Location.hasStartedLocationUpdatesAsync(LOCATION_TASK);
  if (hasStarted) return;
  await Location.startLocationUpdatesAsync(LOCATION_TASK, {
    accuracy: Location.Accuracy.Balanced,
    timeInterval: 15000,
    distanceInterval: 0,
    pausesUpdatesAutomatically: false,
    showsBackgroundLocationIndicator: true,
    foregroundService: {
      notificationTitle: "LocumMap is tracking location",
      notificationBody: "Tracking is active only during your duty window.",
    },
  });
}

async function stopBackgroundTracking() {
  await AsyncStorage.removeItem("locummap_active_assignment_id");
  const hasStarted = await Location.hasStartedLocationUpdatesAsync(LOCATION_TASK);
  if (hasStarted) await Location.stopLocationUpdatesAsync(LOCATION_TASK);
}

export default function App() {
  const [screen, setScreen] = useState<"login" | "profile" | "jobs" | "live">("login");
  const [loading, setLoading] = useState(false);
  const [phone, setPhone] = useState("9100000100");
  const [otp, setOtp] = useState("");
  const [devOtp, setDevOtp] = useState<string | null>(null);

  const [me, setMe] = useState<MeDoctor | null>(null);
  const [fullName, setFullName] = useState("Test Doctor");
  const [specialty, setSpecialty] = useState<MeDoctor["specialty"]>("dentist_general");
  const [regNo, setRegNo] = useState("TN-DENT-12345");

  const [jobs, setJobs] = useState<Shift[]>([]);
  const [active, setActive] = useState<{ shift: Shift; assignmentId: string } | null>(null);
  const [currentLoc, setCurrentLoc] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    (async () => {
      const tok = await AsyncStorage.getItem("locummap_token");
      if (tok) {
        await bootstrap();
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function bootstrap() {
    setLoading(true);
    try {
      const d = await api<MeDoctor>("/doctors/me");
      setMe(d);
      setFullName(d.full_name);
      setSpecialty(d.specialty);
      setRegNo(d.reg_no);
      setScreen("jobs");
      await refreshJobs();
    } catch {
      setScreen("profile");
    } finally {
      setLoading(false);
    }
  }

  async function requestPermissions() {
    const fg = await Location.requestForegroundPermissionsAsync();
    if (fg.status !== "granted") throw new Error("Location permission denied");
    const bg = await Location.requestBackgroundPermissionsAsync();
    // bg may be denied; keep app usable but tracking will be foreground-only
    return bg.status === "granted";
  }

  async function requestOtp() {
    setLoading(true);
    try {
      const res = await api<{ ok: boolean; dev_otp?: string | null }>("/auth/otp/request", {
        method: "POST",
        body: JSON.stringify({ phone, role_hint: "doctor" }),
      });
      setDevOtp(res.dev_otp ?? null);
      Alert.alert("OTP sent", devOtp ? `Demo OTP: ${devOtp}` : "Enter OTP");
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp() {
    setLoading(true);
    try {
      const res = await api<TokenRes>("/auth/otp/verify", {
        method: "POST",
        body: JSON.stringify({ phone, otp, role: "doctor" as Role }),
      });
      await AsyncStorage.setItem("locummap_token", res.access_token);
      await requestPermissions();
      await bootstrap();
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveProfile() {
    setLoading(true);
    try {
      await api("/doctors/me", {
        method: "POST",
        body: JSON.stringify({ full_name: fullName, specialty, reg_no: regNo }),
      });
      await bootstrap();
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function refreshJobs() {
    try {
      const list = await api<Shift[]>("/jobs/available");
      setJobs(list);
    } catch {
      // ignore
    }
  }

  async function acceptShift(shiftId: string) {
    setLoading(true);
    try {
      const res = await api<{ assignment_id: string }>(`/shifts/${shiftId}/book`, { method: "POST", body: "{}" });
      const s = await api<Shift>(`/shifts/${shiftId}`);
      setActive({ shift: s, assignmentId: res.assignment_id });
      setScreen("live");
      await startBackgroundTracking(res.assignment_id);
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function setEnRoute() {
    if (!active) return;
    setLoading(true);
    try {
      await api(`/assignments/${active.assignmentId}/status`, {
        method: "POST",
        body: JSON.stringify({ status: "en_route" }),
      });
      Alert.alert("Updated", "Status set to En Route");
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function pingOnce() {
    if (!active) return;
    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
    setCurrentLoc({ lat: loc.coords.latitude, lng: loc.coords.longitude });
    await api(`/assignments/${active.assignmentId}/location`, {
      method: "POST",
      body: JSON.stringify({
        ts: new Date(loc.timestamp).toISOString(),
        lat: loc.coords.latitude,
        lng: loc.coords.longitude,
        speed: loc.coords.speed ?? null,
        heading: loc.coords.heading ?? null,
        accuracy: loc.coords.accuracy ?? null,
      }),
    });
  }

  async function verifyShiftOtp(type: "checkin" | "checkout") {
    if (!active) return;
    if (!otp.trim()) {
      Alert.alert("OTP required", "Enter the OTP from the clinic.");
      return;
    }
    setLoading(true);
    try {
      const res = await api<{ ok: boolean; status: string }>(
        `/assignments/${active.assignmentId}/otp/verify?type=${type}`,
        { method: "POST", body: JSON.stringify({ otp }) }
      );
      Alert.alert("Success", `Shift status: ${res.status}`);
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function sos() {
    if (!active) return;
    try {
      await api(`/assignments/${active.assignmentId}/sos`, { method: "POST", body: JSON.stringify({ message: "Doctor SOS" }) });
      Alert.alert("Sent", "Clinic notified.");
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    }
  }

  async function endLive() {
    await stopBackgroundTracking();
    setActive(null);
    setScreen("jobs");
    await refreshJobs();
  }

  const Header = ({ title }: { title: string }) => (
    <View style={{ padding: 16 }}>
      <Text style={{ fontSize: 12, fontWeight: "800", color: "#0284c7" }}>LocumMap Chennai</Text>
      <Text style={{ fontSize: 26, fontWeight: "900", marginTop: 4 }}>{title}</Text>
    </View>
  );

  if (loading && screen === "login") {
    return (
      <SafeAreaView style={styles.safe}>
        <Header title="Doctor" />
        <View style={styles.center}>
          <ActivityIndicator />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />

      {screen === "login" ? (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          <Header title="Doctor" />
          <Card>
            <Text style={styles.label}>Phone</Text>
            <TextInput style={styles.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" />
            <Text style={styles.label}>OTP</Text>
            <TextInput style={styles.input} value={otp} onChangeText={setOtp} keyboardType="number-pad" />
            {devOtp ? <Text style={styles.hint}>Demo OTP: {devOtp}</Text> : null}
            <View style={{ flexDirection: "row", gap: 10, marginTop: 12 }}>
              <PrimaryButton title="Get OTP" onPress={requestOtp} disabled={loading} />
              <PrimaryButton title="Verify" onPress={verifyOtp} disabled={loading} />
            </View>
          </Card>
        </ScrollView>
      ) : null}

      {screen === "profile" ? (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          <Header title="Profile" />
          <Card>
            <Text style={styles.label}>Full name</Text>
            <TextInput style={styles.input} value={fullName} onChangeText={setFullName} />
            <Text style={styles.label}>Specialty</Text>
            <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
              <Pill selected={specialty === "dentist_general"} onPress={() => setSpecialty("dentist_general")} title="Dentist" />
              <Pill selected={specialty === "endodontist"} onPress={() => setSpecialty("endodontist")} title="Endodontist" />
              <Pill selected={specialty === "anesthetist"} onPress={() => setSpecialty("anesthetist")} title="Anesthetist" />
            </View>
            <Text style={styles.label}>Registration number</Text>
            <TextInput style={styles.input} value={regNo} onChangeText={setRegNo} />
            <View style={{ marginTop: 12 }}>
              <PrimaryButton title="Save" onPress={saveProfile} disabled={loading} />
            </View>
          </Card>
        </ScrollView>
      ) : null}

      {screen === "jobs" ? (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          <Header title="Available shifts" />
          <View style={{ flexDirection: "row", gap: 10, marginBottom: 12 }}>
            <PrimaryButton title="Refresh" onPress={refreshJobs} />
            <PrimaryButton
              title="Logout"
              onPress={async () => {
                await stopBackgroundTracking();
                await AsyncStorage.removeItem("locummap_token");
                setScreen("login");
              }}
              variant="ghost"
            />
          </View>
          {me?.verification_status !== "approved" ? (
            <Card>
              <Text style={{ fontWeight: "800" }}>Verification: {me?.verification_status ?? "pending"}</Text>
              <Text style={styles.hint}>
                In MVP, an admin approves doctors via /admin/doctors/&lt;doctor_profile_id&gt;/verify.
              </Text>
            </Card>
          ) : null}
          {jobs.map((j) => (
            <Card key={j.id}>
              <Text style={{ fontSize: 16, fontWeight: "900" }}>{j.specialty.replaceAll("_", " ")}</Text>
              <Text style={styles.hint}>{j.address}</Text>
              <Text style={styles.hint}>
                {new Date(j.start_time).toLocaleString()} → {new Date(j.end_time).toLocaleString()}
              </Text>
              <Text style={{ marginTop: 6, fontSize: 18, fontWeight: "900" }}>₹ {j.pay_amount_inr}</Text>
              <View style={{ marginTop: 10 }}>
                <PrimaryButton title="Accept" onPress={() => acceptShift(j.id)} disabled={loading} />
              </View>
            </Card>
          ))}
          {jobs.length === 0 ? <Text style={styles.hint}>No jobs right now.</Text> : null}
        </ScrollView>
      ) : null}

      {screen === "live" && active ? (
        <View style={{ flex: 1 }}>
          <Header title="Live shift" />
          <View style={{ paddingHorizontal: 16, paddingBottom: 12 }}>
            <Text style={{ fontWeight: "900" }}>{active.shift.address}</Text>
            <Text style={styles.hint}>
              Tracking pings every ~15s in background (Android) during your duty window.
            </Text>
          </View>
          <View style={{ flex: 1, marginHorizontal: 16, borderRadius: 18, overflow: "hidden" }}>
            <MapView
              style={{ flex: 1 }}
              initialRegion={{
                latitude: active.shift.lat,
                longitude: active.shift.lng,
                latitudeDelta: 0.03,
                longitudeDelta: 0.03,
              }}
            >
              <Marker coordinate={{ latitude: active.shift.lat, longitude: active.shift.lng }} title="Clinic" />
              {currentLoc ? (
                <Marker coordinate={{ latitude: currentLoc.lat, longitude: currentLoc.lng }} title="You" />
              ) : null}
            </MapView>
          </View>

          <View style={{ padding: 16, gap: 10 }}>
            <PrimaryButton title="Set En Route" onPress={setEnRoute} disabled={loading} />
            <PrimaryButton title="Ping now" onPress={async () => {
              try { await pingOnce(); Alert.alert("OK", "Location sent"); } catch (e) { Alert.alert("Error", e instanceof Error ? e.message : "Failed"); }
            }} disabled={loading} variant="ghost" />
            <Text style={styles.label}>OTP (from clinic)</Text>
            <TextInput style={styles.input} value={otp} onChangeText={setOtp} keyboardType="number-pad" />
            <View style={{ flexDirection: "row", gap: 10 }}>
              <PrimaryButton title="Check-in" onPress={() => verifyShiftOtp("checkin")} disabled={loading} />
              <PrimaryButton title="Check-out" onPress={() => verifyShiftOtp("checkout")} disabled={loading} variant="ghost" />
            </View>
            <View style={{ flexDirection: "row", gap: 10 }}>
              <PrimaryButton title="SOS" onPress={sos} disabled={loading} />
              <PrimaryButton title="End" onPress={endLive} variant="ghost" />
            </View>
          </View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

function PrimaryButton({
  title,
  onPress,
  disabled,
  variant = "primary",
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: "primary" | "ghost";
}) {
  const bg = variant === "primary" ? "#0284c7" : "rgba(255,255,255,0.7)";
  const fg = variant === "primary" ? "white" : "#0b1220";
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: bg, opacity: disabled ? 0.6 : pressed ? 0.9 : 1 },
      ]}
    >
      <Text style={{ color: fg, fontWeight: "900" }}>{title}</Text>
    </Pressable>
  );
}

function Pill({ title, selected, onPress }: { title: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={[
        styles.pill,
        { backgroundColor: selected ? "#0ea5e9" : "rgba(255,255,255,0.7)" },
      ]}
    >
      <Text style={{ color: selected ? "white" : "#0b1220", fontWeight: "800" }}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f0f9ff" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  card: {
    backgroundColor: "rgba(255,255,255,0.7)",
    borderColor: "rgba(2,132,199,0.15)",
    borderWidth: 1,
    borderRadius: 18,
    padding: 14,
    marginBottom: 12,
  },
  label: { fontSize: 12, fontWeight: "900", color: "#0b1220", marginTop: 10, marginBottom: 6 },
  hint: { fontSize: 12, color: "rgba(15,23,42,0.7)", marginTop: 4 },
  input: {
    height: 44,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(2,132,199,0.2)",
    paddingHorizontal: 12,
    backgroundColor: "rgba(255,255,255,0.85)",
  },
  btn: {
    height: 46,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    flex: 1,
  },
  pill: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "rgba(2,132,199,0.15)",
  },
});
