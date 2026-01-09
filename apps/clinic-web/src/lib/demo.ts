export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

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

const now = Date.now();

export const demoShifts: Shift[] = [
  {
    id: "demo-shift-1",
    specialty: "dentist_general",
    start_time: new Date(now + 45 * 60 * 1000).toISOString(),
    end_time: new Date(now + 4 * 60 * 60 * 1000).toISOString(),
    pay_amount_inr: 3500,
    address: "T. Nagar, Chennai",
    lat: 13.0418,
    lng: 80.2341,
    status: "en_route",
    assignment_id: "demo-asg-1",
    doctor_name: "Dr. Meena Iyer",
  },
  {
    id: "demo-shift-2",
    specialty: "endodontist",
    start_time: new Date(now + 6 * 60 * 60 * 1000).toISOString(),
    end_time: new Date(now + 10 * 60 * 60 * 1000).toISOString(),
    pay_amount_inr: 8000,
    address: "Adyar, Chennai",
    lat: 13.0012,
    lng: 80.2565,
    status: "posted",
  },
  {
    id: "demo-shift-3",
    specialty: "anesthetist",
    start_time: new Date(now + 24 * 60 * 60 * 1000).toISOString(),
    end_time: new Date(now + 28 * 60 * 60 * 1000).toISOString(),
    pay_amount_inr: 6000,
    address: "Anna Nagar, Chennai",
    lat: 13.085,
    lng: 80.2101,
    status: "booked",
    assignment_id: "demo-asg-3",
    doctor_name: "Dr. Arun Kumar",
  },
];

export function demoRoute(path: string, init?: RequestInit): unknown {
  // minimal demo responses for UI screenshots
  if (path === "/auth/otp/request") return { ok: true, dev_otp: "123456" };
  if (path === "/auth/otp/verify") return { access_token: "demo-token" };

  if (path === "/clinics/me" && (init?.method ?? "GET") === "GET") {
    return {
      id: "demo-clinic",
      name: "Lakshmi Dental Clinic",
      address: "T. Nagar, Chennai",
      city: "Chennai",
      lat: 13.0418,
      lng: 80.2341,
    };
  }
  if (path === "/clinics/me" && init?.method === "POST") {
    return {
      id: "demo-clinic",
      ...(init?.body ? JSON.parse(String(init.body)) : {}),
    };
  }

  if (path === "/shifts" && (init?.method ?? "GET") === "GET") return demoShifts;
  if (path === "/shifts" && init?.method === "POST") {
    const b = init?.body ? JSON.parse(String(init.body)) : {};
    demoShifts.unshift({
      id: `demo-shift-${Math.random().toString(16).slice(2)}`,
      ...b,
      status: "posted",
      assignment_id: null,
      doctor_name: null,
    });
    return demoShifts[0];
  }

  if (path.startsWith("/shifts/") && path.endsWith("/candidates")) {
    return [
      {
        doctor_user_id: "demo-doc-1",
        doctor_profile_id: "demo-docp-1",
        full_name: "Dr. Meena Iyer",
        specialty: "dentist_general",
        reliability: { on_time_rate: 0.9, avg_rating: 4.7, cancels_count: 1, no_show_count: 0 },
        eta_minutes: 18,
        distance_m: 7200,
      },
      {
        doctor_user_id: "demo-doc-2",
        doctor_profile_id: "demo-docp-2",
        full_name: "Dr. Karthik Rao",
        specialty: "dentist_general",
        reliability: { on_time_rate: 0.82, avg_rating: 4.4, cancels_count: 2, no_show_count: 1 },
        eta_minutes: 29,
        distance_m: 11000,
      },
    ];
  }

  if (path.startsWith("/shifts/") && (init?.method ?? "GET") === "GET") {
    const id = path.split("/")[2];
    const s = demoShifts.find((x) => x.id === id) ?? demoShifts[0];
    return s;
  }

  if (path.startsWith("/shifts/") && path.endsWith("/book")) {
    const id = path.split("/")[2];
    const s = demoShifts.find((x) => x.id === id);
    if (s) {
      s.status = "booked";
      s.assignment_id = s.assignment_id ?? `demo-asg-${Math.random().toString(16).slice(2)}`;
      s.doctor_name = s.doctor_name ?? "Dr. Priya Nair";
    }
    return { shift_id: id, assignment_id: s?.assignment_id ?? "demo-asg-x", status: "booked" };
  }

  if (path.includes("/assignments/") && path.endsWith("/live")) {
    return {
      assignment_id: "demo-asg-1",
      shift_id: "demo-shift-1",
      status: "en_route",
      tracking_active: true,
      last_ping: { ts: new Date().toISOString(), lat: 13.0379, lng: 80.2405, accuracy: 10 },
      timeline: [
        { event_type: "shift_posted", ts: new Date(now - 2 * 60 * 60 * 1000).toISOString(), payload: {} },
        { event_type: "shift_booked", ts: new Date(now - 90 * 60 * 1000).toISOString(), payload: {} },
        { event_type: "en_route", ts: new Date(now - 20 * 60 * 1000).toISOString(), payload: {} },
      ],
    };
  }

  if (path.includes("/otp/create")) return { ok: true, expires_at: new Date(now + 5 * 60 * 1000).toISOString(), dev_otp: "654321" };
  if (path === "/payments/create-order") return { provider: "razorpay", amount_inr: 3500, provider_order_id: "order_demo_123" };

  return {};
}

