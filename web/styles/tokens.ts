/**
 * Design tokens — single source for color, spacing, typography.
 * Keeps the UI internally consistent and themeable in one place.
 */

export const color = {
  // Backgrounds — three-step elevation
  bg0: "#070b11",          // page background
  bg1: "#0d1420",          // panel / sidebar
  bg2: "#142030",          // raised card / hover
  bg3: "#1a2940",          // selected / active

  // Borders
  border: "#1a2330",
  borderStrong: "#2a3a50",

  // Text
  text: "#cfe7e0",          // primary
  textDim: "#7a8a92",       // secondary / meta
  textFaint: "#5a6a72",     // tertiary / placeholder

  // Accent
  accent: "#7fe5d3",        // primary teal
  accentDim: "#4ab09a",
  accentBg: "rgba(127, 229, 211, 0.08)",

  // Severities (safety + grading)
  ok: "#3fa988",
  caution: "#f5c95a",
  warn: "#f08a3a",
  block: "#e85a5a",

  // Tiers (T1..T5 = strongest..weakest)
  t1: "#7fe5d3",
  t2: "#7fc8e5",
  t3: "#a89be5",
  t4: "#e59bc8",
  t5: "#c8966b",
} as const;

export const space = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 36,
} as const;

export const radius = { sm: 3, md: 6, lg: 10 } as const;

export const font = {
  mono: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace",
  sans: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
} as const;

export const SEVERITY_COLOR: Record<string, string> = {
  ok: color.ok,
  caution: color.caution,
  warn: color.warn,
  hard_block: color.block,
};

export const TIER_COLOR: Record<string, string> = {
  T1: color.t1, T2: color.t2, T3: color.t3, T4: color.t4, T5: color.t5,
};
