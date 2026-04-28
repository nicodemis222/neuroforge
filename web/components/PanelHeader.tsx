import React from "react";
import { color, space } from "../styles/tokens";

/**
 * Consistent panel header. Every window in the cockpit gets one of these
 * so the user never has to guess what they're looking at.
 */
export const PanelHeader: React.FC<{
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}> = ({ title, subtitle, right }) => (
  <header style={{
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: `${space.sm}px ${space.md}px`,
    borderBottom: `1px solid ${color.border}`, gap: space.md,
    flexShrink: 0,
  }}>
    <div style={{ minWidth: 0 }}>
      <div style={{
        color: color.accent, fontSize: 11, fontWeight: 600,
        letterSpacing: "0.1em", textTransform: "uppercase",
      }}>
        {title}
      </div>
      {subtitle && (
        <div style={{ color: color.textFaint, fontSize: 10, marginTop: 2 }}>
          {subtitle}
        </div>
      )}
    </div>
    {right && <div style={{ flexShrink: 0 }}>{right}</div>}
  </header>
);
