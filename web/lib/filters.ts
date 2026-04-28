/**
 * Shared filter state — used by Sidebar (which renders the controls)
 * and Scatter (which uses the filtered list to draw points). Lifting it
 * to a hook keeps the two views in lockstep.
 */

import { useMemo, useState } from "react";
import type { Intervention } from "./api";

export type Filters = {
  q: string;
  category: Set<string>;
  tier: Set<string>;
  safety: Set<string>;
  hideEmpty: boolean;
};

export const defaultFilters = (): Filters => ({
  q: "", category: new Set(), tier: new Set(), safety: new Set(), hideEmpty: false,
});

export function useFilters(items: Intervention[]) {
  const [f, setF] = useState<Filters>(defaultFilters());

  const filtered = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return items.filter(it => {
      if (q && !it.name.toLowerCase().includes(q)
            && !it.targets.join(" ").toLowerCase().includes(q)) return false;
      if (f.category.size && !f.category.has(it.category)) return false;
      if (f.tier.size && !f.tier.has(it.expected_tier)) return false;
      if (f.safety.size && !f.safety.has(it.safety_overall)) return false;
      if (f.hideEmpty && it.n_evidence === 0) return false;
      return true;
    });
  }, [items, f]);

  const toggle = (key: keyof Filters, val: string) => setF(prev => {
    const next = new Set(prev[key] as Set<string>);
    next.has(val) ? next.delete(val) : next.add(val);
    return { ...prev, [key]: next };
  });

  const reset = () => setF(defaultFilters());
  const setQ = (q: string) => setF(p => ({ ...p, q }));
  const setHideEmpty = (b: boolean) => setF(p => ({ ...p, hideEmpty: b }));
  const isActive = !!(f.q || f.category.size || f.tier.size || f.safety.size || f.hideEmpty);

  return { filters: f, filtered, toggle, reset, setQ, setHideEmpty, isActive };
}
