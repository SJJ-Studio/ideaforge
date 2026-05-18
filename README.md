# IdeaForge — Internal Validation Dashboard

Solo indie maker validation tooling. Not a product — an internal system.

## What it does

Three-module research pipeline:
1. **Pain Sourcing** — scrapes Reddit + reviews, Claude clusters pain points by frequency/intensity
2. **Competitor Mapping** — analyzes adjacent tools, pricing, and gaps
3. **Score & Decide** — go/no-go verdict with kill criteria and next steps

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend dev server, optional)
- Anthropic API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Run
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

For now — just open `frontend/index.html` directly in a browser.

When you're ready to wire up the API calls, either:
- Add `fetch()` calls to the existing JS in `index.html`
- Or scaffold a proper Next.js frontend: `npx create-next-app@latest frontend`

---

## Build Order

- [x] UI shell (done)
- [x] Backend scaffold with Claude prompts (done)
- [ ] Wire frontend to backend API
- [ ] Add real Reddit scraping via PRAW
- [ ] Add competitor page scraping via Playwright
- [ ] Add Supabase for session persistence
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel

---

## Key files

```
ideaforge/
├── frontend/
│   └── index.html          # Dashboard UI — open directly in browser
├── backend/
│   ├── main.py             # FastAPI app — all three module endpoints
│   └── requirements.txt
└── README.md
```

---

## Adding real scrapers

The backend has clear TODO comments where mock data needs replacing:

**Reddit (Module 1):** Install `praw`, create a Reddit app at reddit.com/prefs/apps, add credentials to `.env`

**Competitor pages (Module 2):** Install `playwright`, run `playwright install chromium`, use the async scraper pattern shown in the comments

**Review sites (G2/Capterra):** These block scrapers aggressively — use their RSS feeds or look for unofficial APIs first before reaching for Playwright
