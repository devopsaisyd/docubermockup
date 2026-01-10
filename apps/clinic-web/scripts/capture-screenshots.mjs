import { chromium } from "playwright";

const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:3005";
const outDir = process.env.OUT_DIR ?? "/workspace/screenshots/clinic-web";

const pages = [
  { path: "/", name: "01-home.png" },
  { path: "/login", name: "02-login.png" },
  { path: "/onboarding", name: "03-onboarding.png" },
  { path: "/shifts", name: "04-shifts-map.png" },
  { path: "/shifts/demo-shift-1", name: "05-shift-detail-live.png" },
  { path: "/admin", name: "06-admin-overview.png" },
  { path: "/admin/staff", name: "07-admin-staff.png" },
  { path: "/admin/billing", name: "08-admin-billing.png" },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

for (const p of pages) {
  await page.goto(baseUrl + p.path, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${outDir}/${p.name}`, fullPage: true });
  console.log("Wrote", `${outDir}/${p.name}`);
}

await browser.close();

