import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
    { ignores: ["dist/**", "node_modules/**", "coverage/**", "**/*.d.ts", "**/generated/**"] },
    js.configs.recommended,
    ...tseslint.configs.recommended,
    {
        // Rules that reported on the code of 2026-11-13 are warnings until a later job fixes them, one rule at a time.
        // The number is the count on that day.
        rules: {
            // 1 on 2026-11-13
            "@typescript-eslint/no-unused-vars": "warn",
        },
    },
);
