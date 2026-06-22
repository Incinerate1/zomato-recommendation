# Phase-wise Implementation Plan: AI-Powered Restaurant Recommendation System

This plan outlines the step-by-step implementation for the Zomato-inspired recommendation engine based on our defined context and architecture.

## User Review Required

> [!IMPORTANT]
> Please review the proposed technology stack and phases. The plan suggests using **FastAPI (Python)** for the backend and **Next.js (React)** for the frontend, utilizing **Groq** for fast LLM inference.
> We also need to decide if we want to store the dataset in **SQLite** for structured querying, or just use an in-memory **Pandas DataFrame** for simplicity. The plan currently proposes SQLite for better querying capabilities.

## Open Questions

> [!WARNING]
> 1. Do you already have a Groq API Key, or will we need to set that up?
> 2. Are you comfortable with using SQLite for the database, or would you prefer a different approach (like Postgres or just Pandas)?
> 3. Should we use TailwindCSS for the frontend styling to achieve the premium, modern look quickly?

## Proposed Phases

### Phase 1: Project Setup and Data Ingestion
- Set up the project directory structure (frontend & backend folders).
- Initialize a Python virtual environment and install backend dependencies (`fastapi`, `uvicorn`, `pandas`, `groq`, `sqlite3`, etc.).
- Download the Hugging Face dataset (`ManikaSaini/zomato-restaurant-recommendation`).
- Write a Python data ingestion script to clean the dataset, normalize columns, and load it into an SQLite database.

### Phase 2: Backend Core (Data Retrieval API)
- Set up a FastAPI server.
- Create a REST endpoint (e.g., `POST /api/recommend`) to receive user preferences (location, budget, cuisine, rating, extra).
- Implement the strict filtering logic (SQL `WHERE` clauses) to query the SQLite database and retrieve the top candidate restaurants that perfectly match the rigid criteria.

### Phase 3: Groq LLM Integration
- Integrate the official Groq Python SDK.
- Design the LLM Prompt: It will take the structured output from Phase 2 and ask the LLM to rank the top 3 and provide a 2-sentence explanation for each based on the user's "extra" preferences (e.g., "romantic").
- Enforce structured JSON output from Groq to easily parse the reasoning and rankings back into the API response.

### Phase 4A: Backend API Finalization & Hardening
- **CORS & Environment**: Ensure CORS is properly configured for the Next.js dev server (`http://localhost:3000`). Validate `.env` loading for the Groq API key.
- **Response Schema Polish**: Standardize all API responses with consistent `success`, `data`, `error` fields for the frontend to consume cleanly.
- **Meta Endpoints**: Confirm `/api/meta/locations` and `/api/meta/cuisines` return properly sorted, deduplicated lists for frontend dropdowns/autocomplete.
- **Error Handling**: Add meaningful HTTP error codes and user-friendly error messages for edge cases (empty location, no results, LLM timeout, etc.).
- **Streaming (Optional)**: Investigate adding a `/api/restaurants/recommend/stream` SSE endpoint so the frontend can show the AI explanation typing out in real-time.

---

### Phase 4B: Premium Frontend Development

This is the most critical phase. The frontend must feel like a **production-grade, premium SaaS application** — not a basic form-and-results page.

#### 4B.1 — Project Initialization
- Initialize a **Next.js (React)** application inside a `frontend/` directory using `npx create-next-app`.
- Use **Vanilla CSS** (CSS Modules or a global stylesheet) for full design control.
- Add **Google Fonts** (Inter for body text, Outfit or Clash Display for headings).
- Set up an `api.js` utility module for all fetch calls to the FastAPI backend (`http://localhost:8000`).

#### 4B.2 — Design System & Tokens
Define a comprehensive design system in `globals.css` (CSS custom properties):

| Token Category | Details |
|---|---|
| **Color Palette** | Dark theme base (`hsl(220, 20%, 8%)` background), vibrant accent gradient (coral → amber → warm orange), muted text tones, card surface colors with subtle transparency |
| **Typography** | `--font-heading: 'Outfit', sans-serif`, `--font-body: 'Inter', sans-serif`. Sizes from `--text-xs` (0.75rem) to `--text-4xl` (2.5rem) with proper line heights |
| **Spacing** | 4px base grid: `--space-1` through `--space-16` |
| **Border Radius** | `--radius-sm` (8px), `--radius-md` (12px), `--radius-lg` (20px), `--radius-full` (9999px) |
| **Shadows** | Layered box-shadows for depth: `--shadow-card`, `--shadow-elevated`, `--shadow-glow` (accent-colored ambient glow) |
| **Transitions** | `--ease-smooth: cubic-bezier(0.4, 0, 0.2, 1)`, durations for hover (150ms), enter (300ms), page (500ms) |
| **Glassmorphism** | `backdrop-filter: blur(16px); background: hsla(220, 20%, 12%, 0.7); border: 1px solid hsla(0, 0%, 100%, 0.08)` |

#### 4B.3 — Page Layout & Structure

**Single-Page Application** with two visual states:

1. **Hero / Input State** — Full-viewport landing with a dramatic hero section and the preference form.
2. **Results State** — Smooth transition to a results view showing the AI recommendations.

**Layout Breakdown:**
```
┌──────────────────────────────────────────┐
│  Navbar (logo + subtle tagline)          │
├──────────────────────────────────────────┤
│                                          │
│  Hero Section                            │
│  ┌────────────────────────────────────┐  │
│  │  Headline: "Discover Your          │  │
│  │  Perfect Restaurant"               │  │
│  │  Subtext: "AI-powered..."          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Preference Form Card (glassmorphism)    │
│  ┌────────────────────────────────────┐  │
│  │  Location [searchable dropdown]    │  │
│  │  Cuisine  [searchable dropdown]    │  │
│  │  Budget   [segmented control]      │  │
│  │  Min Rating [interactive slider]   │  │
│  │  Extra Prefs [text input]          │  │
│  │                                    │  │
│  │  [ 🔍 Get Recommendations ]        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  (After submit — Results Section)        │
│  ┌────────────────────────────────────┐  │
│  │  Query Summary Pill                │  │
│  │                                    │  │
│  │  Recommendation Card #1            │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │  🏆 Rank Badge               │  │  │
│  │  │  Restaurant Name (large)     │  │  │
│  │  │  📍 Address | 🍽 Cuisine      │  │  │
│  │  │  ⭐ Rating  | 💰 Cost        │  │  │
│  │  │                              │  │  │
│  │  │  AI Explanation (styled      │  │  │
│  │  │  quote block with gradient   │  │  │
│  │  │  accent border)              │  │  │
│  │  └──────────────────────────────┘  │  │
│  │                                    │  │
│  │  Card #2 ... Card #3 ...          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Footer                                 │
└──────────────────────────────────────────┘
```

#### 4B.4 — Component Inventory

| Component | Description | Key Design Details |
|---|---|---|
| **Navbar** | Fixed top bar with logo and tagline | Blur backdrop, border-bottom glow, becomes opaque on scroll |
| **HeroSection** | Full-height intro with headline + animated gradient text | Animated gradient on the headline, floating particle/dot pattern in background |
| **PreferenceForm** | The core input form in a glassmorphic card | Searchable dropdowns for Location & Cuisine (populated from API), Segmented toggle for Budget (Low/Medium/High), Custom slider for Min Rating with live value display, Textarea for extra preferences |
| **SearchableDropdown** | Custom dropdown with search/filter | Keyboard navigable, highlights matching text, smooth open/close animation |
| **SegmentedControl** | A pill-toggle selector for budget | Animated sliding highlight indicator |
| **RatingSlider** | Custom range slider | Styled track with gradient fill, floating tooltip showing current value |
| **SubmitButton** | CTA button with gradient background | Hover scale + glow effect, loading spinner state, disabled state |
| **LoadingState** | Shown during API call | Animated skeleton cards with shimmer effect + witty loading text ("Asking our AI sommelier...") |
| **ResultsSection** | Container for recommendation cards | Staggered fade-in entrance animation for each card |
| **RecommendationCard** | Individual restaurant result | Rank badge (🥇🥈🥉), restaurant details grid, AI explanation in a styled blockquote with gradient left-border, subtle hover lift |
| **QuerySummaryPill** | Shows current filter context | Compact pill with icons showing active filters, "Modify Search" button to scroll back up |
| **ErrorState** | Friendly error / no-results display | Illustrated empty state with suggestion text |
| **Footer** | Simple footer | "Powered by Groq AI" badge, links |

#### 4B.5 — Animations & Micro-interactions
- **Page load**: Headline text reveals with a staggered letter/word animation.
- **Form inputs**: Subtle scale-up on focus, glowing border accent.
- **Budget toggle**: Sliding pill indicator with spring physics (CSS transition or JS).
- **Submit button**: Pulse glow on hover, morphs into a loading spinner on click.
- **Results entrance**: Each card fades up with `translateY(30px) → 0` staggered by 150ms.
- **Card hover**: Gentle `translateY(-4px)` lift with enhanced box-shadow.
- **Rating stars**: Animated fill from left to right on results load.
- **Scroll**: Navbar becomes solid/blurred on scroll (Intersection Observer).

#### 4B.6 — Responsive Design
- **Desktop (>1024px)**: Form card centered at max 640px width, results cards at max 720px.
- **Tablet (768–1024px)**: Full-width with adjusted padding.
- **Mobile (<768px)**: Stacked layout, full-width inputs, bottom-sticky CTA button, swipeable card carousel for results.

#### 4B.7 — SEO & Accessibility
- Proper `<title>`, `<meta description>`, Open Graph tags.
- Single `<h1>` for the hero headline, semantic heading hierarchy.
- All inputs have associated `<label>` elements.
- Focus-visible outlines on all interactive elements.
- `aria-live` region for results so screen readers announce new recommendations.
- Color contrast ratios meet WCAG AA standards.

---

### Phase 5: Integration, Polish & End-to-End Testing
- **Wire up frontend ↔ backend**: Ensure the Next.js app correctly calls the FastAPI endpoints, handles CORS, and gracefully manages network errors.
- **Loading UX**: Fine-tune skeleton loaders and loading text rotation during LLM processing time (~2-5 seconds).
- **Error boundaries**: Implement React error boundaries and user-friendly fallback states for API failures.
- **Performance**: Lazy-load non-critical assets, optimize CSS, ensure Lighthouse performance score > 90.
- **End-to-end testing**: Test various input combinations (valid, edge-case, empty) through the full UI → API → LLM pipeline.
- **Final polish**: Review every animation, spacing, and color for consistency and premium feel.

## Verification Plan

### Automated Tests
- Unit tests for the Python data filtering logic to ensure correct candidate sets.
- Backend API integration tests using `httpx` or `TestClient` for all endpoints.
- Frontend component smoke tests (optional, if time permits).

### Manual Verification
- Run the FastAPI server (`uvicorn`) and Next.js dev server (`npm run dev`) locally side by side.
- Test the full flow: open the frontend → select filters → submit → verify the loading state → verify results display correctly with AI explanations.
- Test edge cases: no matching restaurants, missing optional fields, extremely broad/narrow filters.
- Test responsiveness on desktop, tablet, and mobile viewport sizes.
- Verify keyboard navigation and screen reader compatibility on the form.
