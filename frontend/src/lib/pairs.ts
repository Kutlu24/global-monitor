// The site's PRIMARY comparison, stated up front rather than derived: the EU
// against the ORIGINAL BRICS five. Two of the ten BRICS members are EU
// neighbours and three are formal BRICS-application candidates, so "the EU vs
// BRICS" is the comparison a reader actually comes here for - and brics5 is
// the bloc that makes it legible, because the 2024-25 expansion added members
// whose overlap with the EU muddies an economic comparison.
export const FEATURED_PAIR_SLUG = "eu-vs-brics5";

// The 4 blocs that take part in the pairwise compare structure.
const COMPARE_BLOCS = ["brics", "eu", "us", "usmca"] as const;

// A bloc compared against a bloc that CONTAINS it is not a comparison.
// `us` is one of USMCA's three members (US / Canada / Mexico), so
// "United States vs USMCA (NAFTA)" measures a country against an aggregate
// that includes it: the answer is baked into the definition and the page says
// nothing. It is excluded rather than left for the reader to notice.
// Membership is a data property (see blocs.py), so if a future bloc is
// similarly nested, add it here - the API has no "is subset of" relation to
// derive this from.
const DEGENERATE_SLUGS = new Set(["us-vs-usmca"]);

export interface Pair {
  a: string;
  b: string;
  slug: string;
  /** The site's primary comparison; rendered as a featured card/nav entry. */
  featured?: boolean;
}

function makePair(a: string, b: string, featured = false): Pair {
  return { a, b, slug: `${a}-vs-${b}`, ...(featured ? { featured: true } : {}) };
}

const derived: Pair[] = [];
for (let i = 0; i < COMPARE_BLOCS.length; i++) {
  for (let j = i + 1; j < COMPARE_BLOCS.length; j++) {
    const slug = `${COMPARE_BLOCS[i]}-vs-${COMPARE_BLOCS[j]}`;
    if (DEGENERATE_SLUGS.has(slug)) continue;
    derived.push(makePair(COMPARE_BLOCS[i], COMPARE_BLOCS[j]));
  }
}

// Featured first so every consumer that renders PAIRS in order (sidebar,
// homepage, sitemaps) leads with it without needing to sort.
export const PAIRS: Pair[] = [makePair("eu", "brics5", true), ...derived];

export function findPair(slug: string): Pair | undefined {
  return PAIRS.find((p) => p.slug === slug);
}

export const FEATURED_PAIR: Pair = PAIRS[0];
