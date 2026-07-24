/** Curated discovery copy for known taxonomy slugs — no API required. */

export type TaxonomyStory = {
  hint: string;
  story: string;
};

export const CATEGORY_STORIES: Record<string, TaxonomyStory> = {
  music: {
    hint: "Afrobeats · live sets · Detty",
    story: "Live music nights, DJ culture, and stages that move the city.",
  },
  nightlife: {
    hint: "Detty · club nights",
    story: "Club energy, Detty Fridays, and the nights people dress for.",
  },
  comedy: {
    hint: "Open mics · stand-up",
    story: "Open mics, headliners, and rooms that stay laughing past midnight.",
  },
  tech: {
    hint: "Mixers · demo days",
    story: "Founders mixers, product demos, and rooms built for builders.",
  },
  gospel: {
    hint: "Worship · conferences",
    story: "Worship nights, faith conferences, and gatherings with reverence.",
  },
  campus: {
    hint: "Festivals · student nights",
    story: "Campus festivals, student nights, and the energy between lectures.",
  },
  lifestyle: {
    hint: "Parties · culture",
    story: "Culture parties, lifestyle drops, and scenes that set the mood.",
  },
  "food-drink": {
    hint: "Tastings · pop-ups",
    story: "Tastings, pop-ups, and tables where the night starts with flavor.",
  },
  "arts-culture": {
    hint: "Galleries · showcases",
    story: "Galleries, showcases, and creative rooms across the city.",
  },
  business: {
    hint: "Networking · summits",
    story: "Networking nights, summits, and rooms where deals meet culture.",
  },
  community: {
    hint: "Meetups · causes",
    story: "Meetups, causes, and gatherings that grow local community.",
  },
};

export const CITY_STORIES: Record<string, TaxonomyStory> = {
  lagos: {
    hint: "Island · Mainland",
    story: "Africa’s nightlife capital — island heat, mainland pulse, every weekend.",
  },
  ibadan: {
    hint: "Campus · culture",
    story: "Campus energy and culture nights across the city of brown roofs.",
  },
  abuja: {
    hint: "Capital nights",
    story: "Capital nights — polished rooms, policy mixers, and city-light energy.",
  },
  "port-harcourt": {
    hint: "Garden city",
    story: "Garden city nights — oil-city energy with coastal weekend pace.",
  },
};

export function categoryStory(
  slug: string,
  fallbackName?: string,
  fallbackDescription?: string | null,
): TaxonomyStory {
  const known = CATEGORY_STORIES[slug];
  if (known) return known;
  const name = fallbackName || slug.replace(/-/g, " ");
  return {
    hint: "Explore this category",
    story:
      fallbackDescription?.trim() ||
      `${name} on Pàdéyá — browse by city, then refine what’s on.`,
  };
}

export function cityStory(slug: string, fallbackName?: string): TaxonomyStory {
  const known = CITY_STORIES[slug];
  if (known) return known;
  const name = fallbackName || slug.replace(/-/g, " ");
  return {
    hint: "What’s on",
    story: `What’s on in ${name} — drill into categories, weekends, and VIP nights.`,
  };
}
