import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // `data/` holds gitignored research downloads, the PyPSA-Eur checkout and its
  // pixi environment (tens of thousands of files). Without this, `eslint .`
  // walks all of it and takes tens of minutes. `**` is required so nested
  // .pixi/.git contents are skipped too; a bare "data" only ignores the
  // directory entry itself.
  { ignores: ["dist", ".output", ".vinxi", ".wrangler", ".tanstack", "data/**"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "server-only",
              message:
                "TanStack Start does not use the Next.js `server-only` package. Rename the module to `*.server.ts` or mark it with `@tanstack/react-start/server-only`.",
            },
          ],
        },
      ],
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  {
    // shadcn primitives legitimately export variants/variants helpers next to
    // the component, which react-refresh flags. These are vendored files: edit
    // them upstream, not here.
    files: ["src/components/ui/**"],
    rules: { "react-refresh/only-export-components": "off" },
  },
  eslintPluginPrettier,
);
