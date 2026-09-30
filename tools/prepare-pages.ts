import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";

// GitHub Pages has no rewrite engine. Give every published route an HTML entry
// so direct links return 200, and use the SPA shell as the unknown-route 404.
const shell = await readFile("dist/index.html", "utf8");
const docs = (await readdir("docs")).filter((file) => file.endsWith(".md"));
for (const route of ["docs", "targets", ...docs.map((file) => `docs/${file.slice(0, -3)}`)]) {
  await mkdir(`dist/${route}`, { recursive: true });
  await writeFile(`dist/${route}/index.html`, shell);
}
await writeFile("dist/404.html", shell);
await writeFile("dist/.nojekyll", "");
console.log(`Prepared ${docs.length + 2} direct-route entries and a 404 shell.`);
