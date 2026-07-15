import type { GeoAIConfig } from 'geo-ai-core';

export default {
  siteName: "AimFast.Dev",
  siteUrl: "https://aimfast-dev.vercel.app",
  siteDescription:
    "Automated trend discovery platform scanning 31+ sources nightly with LLM pipeline. Tracks 150+ emerging tech terms with Builder Score, stage classification, and cross-source validation. Free, no signup.",
  crawlers: "all",
  provider: {
    Pages: [
      {
        title: "Home — Trend Discovery",
        url: "https://aimfast-dev.vercel.app/",
        description:
          "Daily tracking of new tech terms, concepts, and market signals across 31+ sources. See what's emerging before everyone else.",
      },
      {
        title: "Trends Dashboard",
        url: "https://aimfast-dev.vercel.app/trends",
        description:
          "Browse 150+ emerging tech terms with filterable stage classification (Nascent/Emergent/Validating/Rising), sort by Builder Score, momentum, or mention volume.",
      },
      {
        title: "Reports",
        url: "https://aimfast-dev.vercel.app/reports",
        description:
          "Archived daily trend digests with LLM-generated analysis of top emerging terms and market signals.",
      },
      {
        title: "Articles",
        url: "https://aimfast-dev.vercel.app/articles",
        description:
          "In-depth analysis pieces on emerging technology trends, signals, and market intelligence.",
      },
      {
        title: "Pricing",
        url: "https://aimfast-dev.vercel.app/pricing",
        description:
          "Pricing plans for AimFast.Dev — including the monitoring engine for competitor and topic tracking.",
      },
    ],
  },
} satisfies GeoAIConfig;
