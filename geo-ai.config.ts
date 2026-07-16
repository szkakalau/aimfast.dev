import type { GeoAIConfig } from 'geo-ai-core';

export default {
  siteName: "AimFast.Dev",
  siteUrl: "https://www.aimfast.dev",
  siteDescription:
    "Automated trend discovery platform scanning 31+ sources nightly with LLM pipeline. Tracks 150+ emerging tech terms with Builder Score, stage classification, and cross-source validation. Free, no signup.",
  crawlers: "all",
  provider: {
    Pages: [
      {
        title: "Home — Trend Discovery",
        url: "https://www.aimfast.dev/",
        description:
          "Daily tracking of new tech terms, concepts, and market signals across 31+ sources. See what's emerging before everyone else.",
      },
      {
        title: "Trends Dashboard",
        url: "https://www.aimfast.dev/trends",
        description:
          "Browse 150+ emerging tech terms with filterable stage classification (Nascent/Emergent/Validating/Rising), sort by Builder Score, momentum, or mention volume.",
      },
      {
        title: "Reports",
        url: "https://www.aimfast.dev/reports",
        description:
          "Archived daily trend digests with LLM-generated analysis of top emerging terms and market signals.",
      },
      {
        title: "Articles",
        url: "https://www.aimfast.dev/articles",
        description:
          "In-depth analysis pieces on emerging technology trends, signals, and market intelligence.",
      },
      {
        title: "Pricing",
        url: "https://www.aimfast.dev/pricing",
        description:
          "Pricing plans for AimFast.Dev — including the monitoring engine for topic tracking.",
      },
    ],
  },
} satisfies GeoAIConfig;
