import { StatusBar } from "expo-status-bar";
import * as Location from "expo-location";
import * as TaskManager from "expo-task-manager";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const LOCATION_TASK = "locummap-location-task";
const SCREENSHOT_MODE = process.env.EXPO_PUBLIC_SCREENSHOT_MODE === "true";
const PING_QUEUE_KEY = "locummap_ping_queue";

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

type ChatMessage = {
  id: string;
  kind: "text" | "offer" | string;
  sender_role: string;
  message: string | null;
  offer_amount_inr: number | null;
  offer_status: "proposed" | "accepted" | "rejected" | null;
  created_at: string;
};

function haversineM(lat1: number, lng1: number, lat2: number, lng2: number) {
  const R = 6371000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

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
    // Queue for later flush (offline/temporary failure)
    try {
      const raw = await AsyncStorage.getItem(PING_QUEUE_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      arr.push({ assignmentId, payload });
      await AsyncStorage.setItem(PING_QUEUE_KEY, JSON.stringify(arr.slice(-200)));
    } catch {
      // ignore
    }
  }
});

// Avoid bundling react-native-maps on web builds (not supported).
let NativeMapView: any = null;
let NativeMarker: any = null;
if (Platform.OS !== "web") {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const maps = require("react-native-maps");
  NativeMapView = maps.default;
  NativeMarker = maps.Marker;
}

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

async function flushPingQueue() {
  const token = await AsyncStorage.getItem("locummap_token");
  if (!token) return;
  const raw = await AsyncStorage.getItem(PING_QUEUE_KEY);
  if (!raw) return;
  let items: any[] = [];
  try {
    items = JSON.parse(raw);
  } catch {
    await AsyncStorage.removeItem(PING_QUEUE_KEY);
    return;
  }
  if (!Array.isArray(items) || items.length === 0) return;
  const remaining: any[] = [];
  for (const it of items) {
    try {
      await fetch(`${API_BASE_URL}/assignments/${it.assignmentId}/location`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(it.payload),
      });
    } catch {
      remaining.push(it);
    }
  }
  if (remaining.length === 0) await AsyncStorage.removeItem(PING_QUEUE_KEY);
  else await AsyncStorage.setItem(PING_QUEUE_KEY, JSON.stringify(remaining.slice(-200)));
}

async function registerPushToken() {
  if (SCREENSHOT_MODE) return;
  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "default",
        importance: Notifications.AndroidImportance.DEFAULT,
      });
    }

    const perms = await Notifications.getPermissionsAsync();
    if (perms.status !== "granted") {
      const req = await Notifications.requestPermissionsAsync();
      if (req.status !== "granted") return;
    }

    const projectId =
      (Constants.easConfig as any)?.projectId ||
      (Constants.expoConfig as any)?.extra?.eas?.projectId ||
      undefined;
    const token = await Notifications.getExpoPushTokenAsync({ projectId });
    const jwt = await AsyncStorage.getItem("locummap_token");
    if (!jwt) return;
    await fetch(`${API_BASE_URL}/devices/push-token`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${jwt}` },
      body: JSON.stringify({ token: token.data, platform: "expo" }),
    });
  } catch {
    // ignore
  }
}

export default function App() {
  const [screen, setScreen] = useState<"login" | "profile" | "jobs" | "live" | "earnings">(() => {
    if (!SCREENSHOT_MODE || Platform.OS !== "web") return "login";
    try {
      const q = new URLSearchParams(window.location.search);
      const s = q.get("screen");
      if (s === "profile" || s === "jobs" || s === "live" || s === "login" || s === "earnings") return s;
    } catch {
      // ignore
    }
    return "login";
  });
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
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [chatText, setChatText] = useState("");
  const [offerAmount, setOfferAmount] = useState("3500");
  const shiftSocketRef = useRef<any>(null);
  const lobbySocketRef = useRef<any>(null);
  const [earnings, setEarnings] = useState<any | null>(null);

  useEffect(() => {
    (async () => {
      if (SCREENSHOT_MODE) {
        // Static demo state for screenshots (no network, no permissions).
        setDevOtp("123456");
        setMe({
          id: "demo-docp-1",
          full_name: "Dr. Meena Iyer",
          specialty: "dentist_general",
          reg_no: "TN-DENT-12345",
          verification_status: "approved",
        });
        setFullName("Dr. Meena Iyer");
        setSpecialty("dentist_general");
        setRegNo("TN-DENT-12345");
        setJobs([
          {
            id: "demo-shift-1",
            specialty: "dentist_general",
            start_time: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
            end_time: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(),
            pay_amount_inr: 3500,
            address: "T. Nagar, Chennai",
            lat: 13.0418,
            lng: 80.2341,
            status: "posted",
          },
          {
            id: "demo-shift-2",
            specialty: "dentist_general",
            start_time: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
            end_time: new Date(Date.now() + 12 * 60 * 60 * 1000).toISOString(),
            pay_amount_inr: 4000,
            address: "Mylapore, Chennai",
            lat: 13.0337,
            lng: 80.2692,
            status: "posted",
          },
        ]);
        setActive({
          assignmentId: "demo-asg-1",
          shift: {
            id: "demo-shift-1",
            specialty: "dentist_general",
            start_time: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
            end_time: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(),
            pay_amount_inr: 3500,
            address: "T. Nagar, Chennai",
            lat: 13.0418,
            lng: 80.2341,
            status: "en_route",
            assignment_id: "demo-asg-1",
          },
        });
        setCurrentLoc({ lat: 13.0379, lng: 80.2405 });
        setChat([
          {
            id: "demo-chat-1",
            kind: "text",
            sender_role: "clinic_admin",
            message: "Can you reach by 8:45?",
            offer_amount_inr: null,
            offer_status: null,
            created_at: new Date(Date.now() - 6 * 60 * 1000).toISOString(),
          },
          {
            id: "demo-chat-2",
            kind: "offer",
            sender_role: "doctor",
            message: null,
            offer_amount_inr: 4000,
            offer_status: "proposed",
            created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
          },
        ]);
        setEarnings({
          shifts: [
            {
              shift_id: "demo-shift-1",
              status: "paid",
              amount_inr: 4000,
              start_time: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
              end_time: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000 + 4 * 60 * 60 * 1000).toISOString(),
              invoice_url: "/invoices/demo-shift-1",
            },
          ],
          payouts: [
            {
              shift_id: "demo-shift-1",
              amount_inr: 4000,
              status: "paid",
              paid_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
              created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            },
          ],
        });
        return;
      }
      await flushPingQueue();
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
      await connectLobbySocket(d.specialty);
      await registerPushToken();
    } catch {
      setScreen("profile");
    } finally {
      setLoading(false);
    }
  }

  async function connectLobbySocket(specialty: MeDoctor["specialty"]) {
    try {
      const token = await AsyncStorage.getItem("locummap_token");
      if (!token) return;
      if (!lobbySocketRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const { io } = require("socket.io-client");
        lobbySocketRef.current = io(API_BASE_URL, {
          path: "/ws/socket.io",
          transports: ["websocket"],
          auth: { token },
        });
        lobbySocketRef.current.on("specialty_update", (msg: any) => {
          if (msg?.type === "shift_posted" && msg?.shift?.id) {
            setJobs((prev) => {
              const exists = prev.some((s) => s.id === msg.shift.id);
              if (exists) return prev;
              return [
                {
                  id: msg.shift.id,
                  specialty: msg.shift.specialty,
                  start_time: msg.shift.start_time,
                  end_time: msg.shift.end_time,
                  pay_amount_inr: msg.shift.pay_amount_inr,
                  address: msg.shift.address,
                  lat: msg.shift.lat,
                  lng: msg.shift.lng,
                  status: msg.shift.status,
                },
                ...prev,
              ];
            });
          }
        });
      }
      lobbySocketRef.current.emit("join_specialty", { specialty });
    } catch {
      // ignore
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

  async function loadEarnings() {
    setLoading(true);
    try {
      const res = await api<any>("/billing/doctor/earnings");
      setEarnings(res);
      setScreen("earnings");
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
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
      await refreshChat(shiftId);
      await connectShiftSocket(shiftId);
    } catch (e) {
      Alert.alert("Error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function refreshChat(shiftId: string) {
    try {
      const msgs = await api<ChatMessage[]>(`/shifts/${shiftId}/chat`);
      setChat(msgs);
    } catch {
      // ignore
    }
  }

  async function connectShiftSocket(shiftId: string) {
    try {
      const token = await AsyncStorage.getItem("locummap_token");
      if (!token) return;
      if (!shiftSocketRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const { io } = require("socket.io-client");
        shiftSocketRef.current = io(API_BASE_URL, {
          path: "/ws/socket.io",
          transports: ["websocket"],
          auth: { token },
        });
        shiftSocketRef.current.on("shift_update", async (msg: any) => {
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
                created_at: msg.message.created_at ?? new Date().toISOString(),
              },
            ]);
          }
          if (msg?.type === "offer_update") {
            setChat((prev) =>
              prev.map((m) => (m.id === msg.message_id ? { ...m, offer_status: msg.offer_status ?? m.offer_status } : m))
            );
            // refresh shift price after accept
            try {
              const s = await api<Shift>(`/shifts/${shiftId}`);
              setActive((prev) => (prev ? { ...prev, shift: s } : prev));
            } catch {
              // ignore
            }
          }
        });
      }
      shiftSocketRef.current.emit("join_shift", { shift_id: shiftId });
    } catch {
      // ignore
    }
  }

  async function sendChat(kind: "text" | "offer") {
    if (!active) return;
    setLoading(true);
    try {
      if (kind === "text") {
        const text = chatText.trim();
        if (!text) return;
        const m = await api<ChatMessage>(`/shifts/${active.shift.id}/chat`, {
          method: "POST",
          body: JSON.stringify({ kind: "text", message: text }),
        });
        setChat((prev) => [...prev, m]);
        setChatText("");
      } else {
        const amt = Number(offerAmount);
        if (!Number.isFinite(amt) || amt < 100) throw new Error("Invalid offer amount");
        const m = await api<ChatMessage>(`/shifts/${active.shift.id}/chat`, {
          method: "POST",
          body: JSON.stringify({ kind: "offer", offer_amount_inr: amt }),
        });
        setChat((prev) => [...prev, m]);
      }
    } catch (e) {
      Alert.alert("Chat error", e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function respondOffer(messageId: string, action: "accept" | "reject") {
    if (!active) return;
    setLoading(true);
    try {
      const m = await api<ChatMessage>(`/chat/${messageId}/offer/respond`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      setChat((prev) => prev.map((x) => (x.id === m.id ? m : x)));
      const s = await api<Shift>(`/shifts/${active.shift.id}`);
      setActive((prev) => (prev ? { ...prev, shift: s } : prev));
    } catch (e) {
      Alert.alert("Offer error", e instanceof Error ? e.message : "Failed");
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
    const payload = {
      ts: new Date(loc.timestamp).toISOString(),
      lat: loc.coords.latitude,
      lng: loc.coords.longitude,
      speed: loc.coords.speed ?? null,
      heading: loc.coords.heading ?? null,
      accuracy: loc.coords.accuracy ?? null,
    };
    try {
      await api(`/assignments/${active.assignmentId}/location`, { method: "POST", body: JSON.stringify(payload) });
    } catch {
      const raw = (await AsyncStorage.getItem(PING_QUEUE_KEY)) ?? "[]";
      const arr = JSON.parse(raw);
      arr.push({ assignmentId: active.assignmentId, payload });
      await AsyncStorage.setItem(PING_QUEUE_KEY, JSON.stringify(arr.slice(-200)));
    }
  }

  async function navigateToClinic() {
    if (!active) return;
    const { lat, lng } = active.shift;
    const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${lat},${lng}`)}&travelmode=driving`;
    try {
      await Linking.openURL(url);
    } catch {
      Alert.alert("Navigation", "Could not open Google Maps.");
    }
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
    try {
      shiftSocketRef.current?.disconnect?.();
    } catch {
      // ignore
    }
    shiftSocketRef.current = null;
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
            <PrimaryButton title="Earnings" onPress={loadEarnings} variant="ghost" />
            <PrimaryButton
              title="Logout"
              onPress={async () => {
                await stopBackgroundTracking();
                try {
                  lobbySocketRef.current?.disconnect?.();
                } catch {
                  // ignore
                }
                lobbySocketRef.current = null;
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

      {screen === "earnings" ? (
        <ScrollView contentContainerStyle={{ padding: 16 }}>
          <Header title="Earnings" />
          <View style={{ flexDirection: "row", gap: 10, marginBottom: 12 }}>
            <PrimaryButton title="Back" onPress={() => setScreen("jobs")} variant="ghost" />
            <PrimaryButton title="Refresh" onPress={loadEarnings} />
          </View>
          <Card>
            <Text style={{ fontWeight: "900" }}>Payouts</Text>
            {(earnings?.payouts ?? []).map((p: any) => (
              <View key={p.shift_id} style={{ marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: "rgba(2,132,199,0.12)" }}>
                <Text style={{ fontWeight: "900" }}>₹ {p.amount_inr}</Text>
                <Text style={styles.hint}>Status: {String(p.status).toUpperCase()}</Text>
                <Text style={styles.hint}>Paid: {p.paid_at ? new Date(p.paid_at).toLocaleString() : "-"}</Text>
              </View>
            ))}
            {(earnings?.payouts ?? []).length === 0 ? <Text style={styles.hint}>No payouts yet.</Text> : null}
          </Card>
          <Card>
            <Text style={{ fontWeight: "900" }}>Invoices</Text>
            <Text style={styles.hint}>Open invoice links on web for tax docs (HTML → Print to PDF).</Text>
            {(earnings?.shifts ?? []).map((s: any) => (
              <View key={s.shift_id} style={{ marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: "rgba(2,132,199,0.12)" }}>
                <Text style={{ fontWeight: "900" }}>₹ {s.amount_inr}</Text>
                <Text style={styles.hint}>Status: {String(s.status).toUpperCase()}</Text>
                <Text style={styles.hint}>
                  {new Date(s.start_time).toLocaleString()} → {new Date(s.end_time).toLocaleString()}
                </Text>
              </View>
            ))}
            {(earnings?.shifts ?? []).length === 0 ? <Text style={styles.hint}>No invoices yet.</Text> : null}
          </Card>
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
            {Platform.OS === "web" ? (
              <View style={styles.webMap}>
                <View style={styles.webPin}>
                  <Text style={{ fontWeight: "900" }}>Clinic</Text>
                  <Text style={styles.hint}>
                    {active.shift.lat.toFixed(4)}, {active.shift.lng.toFixed(4)}
                  </Text>
                </View>
                <View style={[styles.webPin, { top: 160, left: 190, borderColor: "rgba(16,185,129,0.35)" }]}>
                  <Text style={{ fontWeight: "900" }}>You</Text>
                  <Text style={styles.hint}>
                    {(currentLoc?.lat ?? 13.0379).toFixed(4)}, {(currentLoc?.lng ?? 80.2405).toFixed(4)}
                  </Text>
                </View>
              </View>
            ) : (
              <NativeMapView
                style={{ flex: 1 }}
                initialRegion={{
                  latitude: active.shift.lat,
                  longitude: active.shift.lng,
                  latitudeDelta: 0.03,
                  longitudeDelta: 0.03,
                }}
              >
                <NativeMarker coordinate={{ latitude: active.shift.lat, longitude: active.shift.lng }} title="Clinic" />
                {currentLoc ? (
                  <NativeMarker coordinate={{ latitude: currentLoc.lat, longitude: currentLoc.lng }} title="You" />
                ) : null}
              </NativeMapView>
            )}
          </View>

          <View style={{ padding: 16, gap: 10 }}>
            {/* Find each other: live distance + navigate */}
            <View style={[styles.card, { marginBottom: 0 }]}>
              <Text style={{ fontWeight: "900" }}>Meetup</Text>
              <Text style={styles.hint}>
                Clinic: {active.shift.lat.toFixed(4)}, {active.shift.lng.toFixed(4)}
              </Text>
              {currentLoc ? (
                <Text style={styles.hint}>
                  Distance: {Math.round(haversineM(currentLoc.lat, currentLoc.lng, active.shift.lat, active.shift.lng) / 1000)} km (approx)
                </Text>
              ) : null}
              <View style={{ flexDirection: "row", gap: 10, marginTop: 10 }}>
                <PrimaryButton title="Navigate" onPress={navigateToClinic} />
                <PrimaryButton title="Ping now" onPress={async () => {
                  try { await pingOnce(); Alert.alert("OK", "Location sent"); } catch (e) { Alert.alert("Error", e instanceof Error ? e.message : "Failed"); }
                }} disabled={loading} variant="ghost" />
              </View>
            </View>

            <PrimaryButton title="Set En Route" onPress={setEnRoute} disabled={loading} />
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

            {/* Chat + negotiation */}
            <Text style={[styles.label, { marginTop: 6 }]}>Chat & negotiation</Text>
            <View style={[styles.card, { marginBottom: 0 }]}>
              <ScrollView style={{ maxHeight: 180 }}>
                {chat.map((m) => (
                  <View
                    key={m.id}
                    style={{
                      padding: 10,
                      borderRadius: 14,
                      borderWidth: 1,
                      borderColor: "rgba(2,132,199,0.15)",
                      backgroundColor: m.sender_role.startsWith("clinic") ? "rgba(2,132,199,0.06)" : "rgba(255,255,255,0.7)",
                      marginBottom: 8,
                    }}
                  >
                    <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                      <Text style={{ fontWeight: "900", fontSize: 11 }}>{m.sender_role.toUpperCase()}</Text>
                      <Text style={{ fontSize: 11, color: "rgba(15,23,42,0.6)" }}>
                        {new Date(m.created_at).toLocaleTimeString()}
                      </Text>
                    </View>
                    {m.kind === "offer" ? (
                      <>
                        <Text style={{ marginTop: 4, fontWeight: "900" }}>Offer: ₹ {m.offer_amount_inr}</Text>
                        <Text style={{ marginTop: 2, fontSize: 12, color: "rgba(15,23,42,0.7)" }}>
                          Status: {(m.offer_status ?? "proposed").toUpperCase()}
                        </Text>
                        {m.offer_status === "proposed" && m.sender_role.startsWith("clinic") ? (
                          <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
                            <PrimaryButton title="Reject" onPress={() => respondOffer(m.id, "reject")} variant="ghost" />
                            <PrimaryButton title="Accept" onPress={() => respondOffer(m.id, "accept")} />
                          </View>
                        ) : null}
                      </>
                    ) : (
                      <Text style={{ marginTop: 4 }}>{m.message}</Text>
                    )}
                  </View>
                ))}
                {chat.length === 0 ? <Text style={styles.hint}>No messages yet.</Text> : null}
              </ScrollView>

              <Text style={styles.label}>Message</Text>
              <TextInput style={styles.input} value={chatText} onChangeText={setChatText} />
              <View style={{ flexDirection: "row", gap: 10, marginTop: 10 }}>
                <PrimaryButton title="Send" onPress={() => sendChat("text")} disabled={loading} />
              </View>

              <Text style={styles.label}>Offer amount (₹)</Text>
              <TextInput style={styles.input} value={offerAmount} onChangeText={setOfferAmount} keyboardType="number-pad" />
              <View style={{ flexDirection: "row", gap: 10, marginTop: 10 }}>
                <PrimaryButton title="Propose" onPress={() => sendChat("offer")} disabled={loading} variant="ghost" />
              </View>
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
  webMap: {
    flex: 1,
    backgroundColor: "#e0f2fe",
    borderWidth: 1,
    borderColor: "rgba(2,132,199,0.18)",
    borderRadius: 18,
    position: "relative",
    overflow: "hidden",
  },
  webPin: {
    position: "absolute",
    top: 90,
    left: 120,
    backgroundColor: "rgba(255,255,255,0.85)",
    borderRadius: 16,
    padding: 10,
    borderWidth: 1,
    borderColor: "rgba(2,132,199,0.25)",
  },
});
