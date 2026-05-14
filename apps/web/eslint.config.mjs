import nextPlugin from "eslint-config-next";

export default [
  {
    ignores: [".next/**", "node_modules/**", "dist/**"],
  },
  ...nextPlugin,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
];
