import { mkdir, readFile, readdir, writeFile, rm } from "node:fs/promises";

// GitHub Pages has no rewrite engine. Give every published route an HTML entry
// so direct links return 200, and use the SPA shell as the unknown-route 404.
const shell = await readFile("dist/index.html", "utf8");
const docs = (await readdir("docs")).filter((file) => file.endsWith(".md"));
for (const route of ["docs", ...docs.map((file) => `docs/${file.slice(0, -3)}`)]) {
  await mkdir(`dist/${route}`, { recursive: true });
  await writeFile(`dist/${route}/index.html`, shell);
}
await writeFile("dist/404.html", shell);
await writeFile("dist/.nojekyll", "");
console.log(`Prepared ${docs.length + 1} direct-route entries and a 404 shell.`);

// Hydrated calculation metadata stays local; publish its lossless gzip archive.
for (const path of [
  "irena-capacity-2025/summary.json",
  "european-reservoir-clearing-2025/summary.json",
  "fixed-reservoir-screening-2025/summary.json",
  "daily-fuel-annual-2025/summary.json",
]) {
  await rm(`dist/research/${path}`, { force: true });
}
