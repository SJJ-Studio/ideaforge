from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import anthropic
import httpx
import os

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="IdeaForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── Models ────────────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    niche: str
    idea: Optional[str] = None
    audience: Optional[str] = None
    sources: List[str] = ["reddit", "reviews", "g2", "competitors"]
    raw_text: Optional[str] = None

class SubredditSuggestion(BaseModel):
    subreddits: List[str]
    reasoning: str

class PainPoint(BaseModel):
    theme: str
    frequency: str       # high / medium / low
    intensity: str       # high / medium / low
    evidence: List[str]  # raw quotes or examples

class CompetitorResult(BaseModel):
    name: str
    pricing: str
    strengths: List[str]
    weaknesses: List[str]
    gap: str

class ScoreRequest(BaseModel):
    niche: str
    idea: Optional[str] = None
    audience: Optional[str] = None
    sources: List[str] = ["reddit", "reviews", "g2", "competitors"]
    pain_points: List[PainPoint] = []
    competitors: List[CompetitorResult] = []

class ScoreResult(BaseModel):
    score: int           # 0-100
    verdict: str         # GO / WATCH / KILL
    reasoning: str
    suggested_price_range: str
    kill_criteria_flags: List[str]
    next_steps: List[str]

# ── Module 0: Subreddit Suggestion ───────────────────────────────────────────────────
@app.post("/research/suggest-subreddits", response_model=SubredditSuggestion)
async def suggest_subreddits(req: ResearchRequest):
    prompt = f"""
    You are a Reddit community expert helping a researcher find the best subreddits to source pain points.
    
    Niche: "{req.niche}"
    Specific idea: {req.idea or "not specified"}
    Target audience: {req.audience or "not specified"}
    
    Suggest 5-8 subreddits that would have the most relevant discussions, complaints, and pain points for this niche.
    Prioritize communities where people actively discuss problems and frustrations, not just general interest communities.
    
    Respond in JSON only with keys:
    - subreddits (array of strings, just the subreddit name without r/)
    - reasoning (one sentence explaining the selection)
    
    No markdown, no explanation, just valid JSON.
    """

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        result = json.loads(message.content[0].text)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse Claude response")

# ── Module 1: Pain Sourcing ───────────────────────────────────────────────────

@app.post("/research/pain-sourcing", response_model=List[PainPoint])
async def pain_sourcing(req: ResearchRequest):
    """
    Scrape Reddit and reviews, then use Claude to cluster and rank pain points.
    In production: replace mock data with real PRAW / Playwright scrapers.
    """
    # TODO: Replace with real Reddit scraping via PRAW
    # import praw
    # reddit = praw.Reddit(client_id=..., client_secret=..., user_agent=...)
    # posts = reddit.subreddit("digitalnomad+solotravel").search(req.niche, limit=100)
    # raw_text = "\n".join([p.title + " " + p.selftext for p in posts])

    raw_text = req.raw_text or f"No data provided for niche: {req.niche}"

    prompt = f"""
    You are a market research analyst helping an indie developer find product opportunities.
    
    Here is raw community feedback about the niche: "{req.niche}"
    Target audience: {req.audience or "general"}
    
    RAW DATA:
    {raw_text}
    
    Extract and cluster the top 3-5 pain points. For each, provide:
    - A clear theme name (short)
    - Frequency: how often this comes up (high/medium/low)
    - Intensity: how frustrated people seem (high/medium/low)  
    - 2-3 pieces of evidence (quotes or paraphrased examples)
    
    Respond in JSON only. Array of objects with keys: theme, frequency, intensity, evidence (array of strings).
    No markdown, no explanation, just valid JSON.
    """

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        result = json.loads(message.content[0].text)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse Claude response")


# ── Module 2: Competitor Mapping ──────────────────────────────────────────────

@app.post("/research/competitor-mapping", response_model=List[CompetitorResult])
async def competitor_mapping(req: ResearchRequest):
    """
    Analyze competitors using Claude. In production: use Playwright to scrape
    pricing pages and review sites, feed that raw HTML/text into this prompt.
    """
    # TODO: Real competitor scraping
    # async with async_playwright() as p:
    #     browser = await p.chromium.launch()
    #     page = await browser.new_page()
    #     await page.goto("https://wanderlog.com/pricing")
    #     pricing_text = await page.inner_text("body")

    prompt = f"""
    You are a competitive intelligence analyst.
    
    Niche: "{req.niche}"
    Specific idea: {req.idea or "not specified"}
    
    Identify 3-4 real competitor tools in this space (use your training knowledge).
    For each provide:
    - name: product name
    - pricing: what they charge (free / freemium / price per month)
    - strengths: list of 2-3 things they do well
    - weaknesses: list of 2-3 things users complain about
    - gap: one sentence on the specific gap they leave open
    
    Respond in JSON only. Array of objects. No markdown, no explanation.
    """

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        result = json.loads(message.content[0].text)
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse Claude response")


# ── Module 3: Scoring & Decision ─────────────────────────────────────────────

@app.post("/research/score", response_model=ScoreResult)
async def score_idea(req: ScoreRequest):
    """
    Apply scoring framework to produce a go/no-go verdict.
    Takes outputs from modules 1 and 2 as input.
    """
    pain_summary = "\n".join([
        f"- {p.theme} (frequency: {p.frequency}, intensity: {p.intensity})"
        for p in req.pain_points
    ])

    competitor_summary = "\n".join([
        f"- {c.name}: {c.pricing} | Gap: {c.gap}"
        for c in req.competitors
    ])

    prompt = f"""
    You are an experienced indie maker and startup validator.
    
    Evaluate this product idea using a rigorous scoring framework.
    
    NICHE: {req.niche}
    IDEA: {req.idea or "undefined — evaluate the niche broadly"}
    AUDIENCE: {req.audience or "not specified"}
    
    PAIN POINTS FOUND:
    {pain_summary or "None provided yet"}
    
    COMPETITOR LANDSCAPE:
    {competitor_summary or "None provided yet"}
    
    Score this opportunity from 0-100 based on:
    - Pain frequency and intensity (25 points)
    - Willingness to pay signal (20 points)  
    - Gap size vs competitors (20 points)
    - Reachability of target audience (20 points)
    - Buildability by a solo developer (15 points)
    
    Verdict rules:
    - 70+ = GO (strong signal, move to user interviews)
    - 40-69 = WATCH (some signal, needs more validation)
    - Under 40 = KILL (insufficient signal, move on)
    
    Respond in JSON only with keys:
    - score (integer 0-100)
    - verdict (GO / WATCH / KILL)
    - reasoning (2-3 sentences)
    - suggested_price_range (e.g. "$8-15/month")
    - kill_criteria_flags (array of strings — things that could kill this idea)
    - next_steps (array of 3 concrete next actions)
    
    No markdown, no explanation, just valid JSON.
    """ 

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    import json
    try:
        result = json.loads(message.content[0].text)
        try:
            supabase.table("sessions").insert({
                "niche": req.niche,
                "idea": req.idea,
                "audience": req.audience,
                "subreddits": req.sources,
                "pain_points": [p.dict() for p in req.pain_points],
                "competitors": [c.dict() for c in req.competitors],
                "score": result["score"],
                "verdict": result["verdict"],
                "reasoning": result["reasoning"],
                "suggested_price_range": result["suggested_price_range"],
                "kill_criteria_flags": result["kill_criteria_flags"],
                "next_steps": result["next_steps"]
            }).execute()
        except Exception as e:
            print(f"Failed to save session: {e}")
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse Claude response")


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

# ── Stats check ──────────────────────────────────────────────────────────────

@app.get("/stats")
async def get_stats():
    try:
        sessions = supabase.table("sessions").select("score, verdict, niche").execute()
        data = sessions.data
        
        total_sessions = len(data)
        top_score = max([s["score"] for s in data], default=0)
        top_score_niche = next((s["niche"] for s in data if s["score"] == top_score), "")
        go_count = len([s for s in data if s["verdict"] == "GO"])
        unique_niches = len(set([s["niche"] for s in data]))
        
        return {
            "total_sessions": total_sessions,
            "unique_niches": unique_niches,
            "top_score": top_score,
            "top_score_niche": top_score_niche,
            "go_count": go_count
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_sessions": 0,
            "unique_niches": 0,
            "top_score": 0,
            "top_score_niche": "",
            "go_count": 0
        }
    
# ── Sessions list ─────────────────────────────────────────────────────────────
@app.get("/sessions")
async def get_sessions():
    try:
        sessions = supabase.table("sessions").select("*").order("created_at", desc=True).execute()
        return sessions.data
    except Exception as e:
        print(f"Sessions error: {e}")
        return []
    
# ── Reddit proxy ──────────────────────────────────────────────────────────────
@app.get("/proxy/reddit")
async def reddit_proxy(subreddit: str, q: str):
    try:
        url = f"https://www.reddit.com/r/{subreddit}/search.json?q={q}&limit=10&sort=relevance&t=year&restrict_sr=1"
        async with httpx.AsyncClient(headers={"User-Agent": "ideaforge-research/0.1"}) as client_http:
            res = await client_http.get(url)
            if res.status_code == 403:
                return {"data": {"children": []}}
            return res.json()
    except Exception as e:
        print(f"Reddit proxy error: {e}")
        return {"data": {"children": []}}