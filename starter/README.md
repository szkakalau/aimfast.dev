# Starter Design System

Drop-in CSS foundation for making any project look premium. ~5KB gzipped.

## Quick Start

```bash
# 1. Copy the file
cp starter/design-system.css your-project/app/

# 2. Install Lucide icons (optional but recommended)
npm install lucide-react

# 3. Import in your layout or globals CSS
# Next.js:  @import './design-system.css';
# Plain:    <link rel="stylesheet" href="design-system.css">
```

## Customize Branding

Open `design-system.css`, search for `BRAND`, change 3 lines:

```css
--color-accent:       #YOUR_COLOR;   /* primary brand color */
--color-accent-hover: #YOUR_DARKER;  /* hover state */
--color-accent-muted: oklch(...);    /* 10% opacity version */
```

Optionally swap fonts:

```css
--font-heading: 'Your Font', sans-serif;
--font-body:    'Your Font', sans-serif;
--font-mono:    'Your Mono Font', monospace;
```

## What You Get

| Feature | Class | Example |
|---------|-------|---------|
| Shadow cards (no borders!) | `.card` | `<div class="card">...</div>` |
| Accent card | `.card-accent` | Left color stripe |
| Primary button | `.btn .btn-primary` | `<button class="btn btn-primary">` |
| Outline button | `.btn .btn-outline` | Secondary action |
| Badge | `.badge` | Small label |
| Eyebrow | `.eyebrow` | Section label |
| Container | `.container` | Centered 1100px |
| Divider | `.hr` | `<hr class="hr">` |
| Inline icon | `.icon-inline` | Icon next to text |
| Fade-up animation | `.anim-fade-up` | Scroll entrance |
| Skeleton loader | `.skeleton` | Loading placeholder |

## Design Principles

1. **No borders on cards** — use shadows for depth
2. **Sans-serif headings** — mono only for code/data
3. **8px spacing rhythm** — use `var(--space-1)` through `var(--space-12)`
4. **Multi-layer shadows** — `xs → sm → md → lg → xl` for realistic elevation
5. **Hover = lift** — cards translateY(-1px) + shadow increase on hover

## Typography Setup

```html
<!-- Google Fonts (add to <head>) -->
<link href="https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

## Lucide Icon Cheatsheet

```tsx
import { Clock, Eye, TrendingDown, Search, Shield, Target, BarChart3, Banknote, Zap, ClipboardList, X } from 'lucide-react';

// Decorative (large)
<Search size={32} className="engine-icon" />

// Inline (small, next to text)
<Target size={16} className="icon-inline" />
```

## Origin

Extracted from [AimFast.Dev](https://aimfast.dev) design system, built through iterative refinement against top-300 AI SaaS benchmarks.
