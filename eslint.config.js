import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // `data/` holds the gitignored PyPSA-Eur checkout and its pixi environment
  // (tens of thousands of files). Without this, `eslint .` walks all of it and
  // takes tens of minutes. `**` is required so nested .pixi/.git contents are
  // skipped too; a bare "data" only ignores the directory entry itself.
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
  eslintPluginPrettier,
  // Lovable regenerates the Supabase integration from the live schema. Five of the six
  // files carry an explicit "automatically generated, do not edit" header and types.ts is
  // generated into the repo as well. Reformatting them here would be undone on the next
  // schema push, so they are excluded from the two rules that only reflect local style
  // rather than correctness. `tsc` still typechecks all of them.
  {
    files: ["src/integrations/supabase/**/*.ts"],
    rules: {
      "prettier/prettier": "off",
      "react-refresh/only-export-components": "off",
      // previewAuthStorage declares `let timer` and assigns it once, after the closure
      // that clears it is defined. `const` would require hoisting the setTimeout call,
      // which is a restructure of code we do not own.
      "prefer-const": "off",
    },
  },
  // shadcn/ui components deliberately export a `*Variants` style constant next to the
  // component so callers can compose the same classes. That is the upstream pattern for
  // every file under components/ui, and re-running `shadcn add` would restore the warning.
  {
    files: ["src/components/ui/**/*.tsx"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
);
