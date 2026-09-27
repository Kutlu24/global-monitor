// The 6 pairwise combinations of the 4 blocs that participate in the main
// compare structure - brics5 deliberately excluded (see blocs.py's own
// docstring: it's a secondary historical view of `brics`, not a 5th
// comparison target, so this stays 4 blocs -> C(4,2) = 6 pairs, not 10).
const COMPARE_BLOCS = ["brics", "eu", "us", "usmca"] as const;

export interface Pair {
  a: string;
  b: string;
  slug: string;
}

export const PAIRS: Pair[] = [];
for (let i = 0; i < COMPARE_BLOCS.length; i++) {
  for (let j = i + 1; j < COMPARE_BLOCS.length; j++) {
    const a = COMPARE_BLOCS[i];
    const b = COMPARE_BLOCS[j];
    PAIRS.push({ a, b, slug: `${a}-vs-${b}` });
  }
}

export function findPair(slug: string): Pair | undefined {
  return PAIRS.find((p) => p.slug === slug);
}
