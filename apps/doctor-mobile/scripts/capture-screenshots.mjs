import { chromium } from "playwright";

const baseUrl = process.env.BASE_URL ?? "http://127.0.0.1:3006";
const outDir = process.env.OUT_DIR ?? "/workspace/screenshots/doctor-mobile";

const pages = [
  { path: "/?screen=login", name: "01-login.png" },
  { path: "/?screen=profile", name: "02-profile.png" },
  { path: "/?screen=jobs", name: "03-jobs.png" },
  { path: "/?screen=live", name: "04-live-shift.png" },
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 430, height: 932 } }); // iPhone-ish frame

for (const p of pages) {
  await page.goto(baseUrl + p.path, { waitUntil: "networkidle" });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${outDir}/${p.name}`, fullPage: true });
  console.log("Wrote", `${outDir}/${p.name}`);
}

await browser.close();

