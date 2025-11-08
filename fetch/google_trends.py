"""
google_trends.py
Fixed Google Trends scraper with proper rate limiting and caching
"""

import time
import random
import requests
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]

# Cache directory
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Minimum time between requests (in seconds)
MIN_REQUEST_INTERVAL = 60  # 1 minute between Google Trends requests
LAST_REQUEST_FILE = CACHE_DIR / "last_google_request.txt"


def can_make_request():
    """Check if enough time has passed since last request"""
    if not LAST_REQUEST_FILE.exists():
        return True
    
    try:
        with open(LAST_REQUEST_FILE, 'r') as f:
            last_request_time = float(f.read().strip())
        
        time_since_last = time.time() - last_request_time
        
        if time_since_last < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - time_since_last
            print(f"⏳ Rate limit: Need to wait {wait_time:.0f} seconds before next request")
            return False
        
        return True
    except:
        return True


def record_request_time():
    """Record the time of the current request"""
    with open(LAST_REQUEST_FILE, 'w') as f:
        f.write(str(time.time()))


def get_cached_results(cache_key, max_age_hours=1):
    """Get cached results if they exist and are fresh"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
        
        cache_time = datetime.fromisoformat(cached_data['timestamp'])
        age = datetime.now() - cache_time
        
        if age.total_seconds() < max_age_hours * 3600:
            print(f"✅ Using cached data (age: {age.total_seconds()/60:.1f} minutes)")
            return cached_data['results']
        
        print(f"⚠️ Cache expired (age: {age.total_seconds()/3600:.1f} hours)")
        return None
    
    except Exception as e:
        print(f"⚠️ Cache read error: {e}")
        return None


def save_to_cache(cache_key, results):
    """Save results to cache"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': results
            }, f, indent=2)
        print(f"✅ Results cached to {cache_file}")
    except Exception as e:
        print(f"⚠️ Cache save error: {e}")


def fetch_dynamic_keywords():
    """Fetch keywords from Google autocomplete with rate limiting"""
    seed_terms = [
        "education", "exam", "online course", 
        "study tips", "scholarship"
    ]
    
    all_keywords = set(seed_terms)
    
    for seed in seed_terms[:3]:  # Limit to 3 to avoid rate limits
        try:
            url = "https://suggestqueries.google.com/complete/search"
            params = {
                "client": "firefox",
                "q": seed,
            }
            r = requests.get(url, params=params, timeout=5)
            
            if r.status_code == 200:
                suggestions = r.json()[1]
                all_keywords.update(suggestions[:2])
            
            # Rate limiting between autocomplete requests
            time.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            print(f"⚠️ Autocomplete failed for '{seed}': {e}")
            continue
    
    keywords = list(all_keywords)[:10]
    print(f"✅ Auto keywords discovered: {keywords}")
    return keywords


def fetch_google_trends(geo="IN", timeframe="now 1-d", use_cache=True, cache_hours=1):
    """
    Fetch Google Trends with proper rate limiting and caching
    
    Args:
        geo: Geographic location (default: IN for India)
        timeframe: Time range (default: now 1-d)
        use_cache: Whether to use cached results (default: True)
        cache_hours: Maximum age of cache in hours (default: 1)
    
    Returns:
        list: Trending keywords with scores
    """
    
    cache_key = f"google_trends_{geo}_{timeframe}"
    
    # Try to use cache first
    if use_cache:
        cached = get_cached_results(cache_key, max_age_hours=cache_hours)
        if cached:
            return cached
    
    # Check rate limiting
    if not can_make_request():
        print("❌ Rate limit reached. Using fallback or cached data.")
        # Try to use older cache
        cached = get_cached_results(cache_key, max_age_hours=24)
        if cached:
            print("✅ Using older cached data (up to 24h old)")
            return cached
        return []
    
    print("🔍 Fetching fresh data from Google Trends...")
    
    keywords = fetch_dynamic_keywords()
    
    # Fix for urllib3 compatibility issue
    try:
        pytrends = TrendReq(
            hl="en-US",
            tz=330,
            timeout=(10, 30),
            retries=2,
            backoff_factor=0.5,
            requests_args={"headers": {"User-Agent": random.choice(USER_AGENTS)}}
        )
    except TypeError:
        # Fallback for older pytrends versions
        pytrends = TrendReq(
            hl="en-US",
            tz=330,
            requests_args={"headers": {"User-Agent": random.choice(USER_AGENTS)}}
        )
    
    try:
        # Build payload
        pytrends.build_payload(
            kw_list=keywords,
            timeframe=timeframe,
            geo=geo
        )
        
        # Record that we're making a request
        record_request_time()
        
        # Try related_queries with exponential backoff
        data = None
        for attempt in range(3):
            try:
                data = pytrends.related_queries()
                break
            except Exception as e:
                if "429" in str(e):
                    wait_time = (2 ** attempt) * 30  # 30s, 60s, 120s
                    print(f"⚠️ Rate limited (attempt {attempt+1}/3). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"⚠️ Error (attempt {attempt+1}/3): {str(e)[:100]}")
                    time.sleep(random.uniform(5, 10))
        
        if data is None:
            print("❌ related_queries failed after retries — using fallback")
            return fallback_interest(pytrends, keywords, cache_key)
        
        results = []
        seen_keywords = set()
        
        # Process rising and top queries
        for key in data:
            # Rising queries
            rising = data[key].get("rising")
            if rising is not None and not rising.empty:
                for _, row in rising.iterrows():
                    kw = row['query'].lower().strip()
                    if kw not in seen_keywords:
                        score = 100 if row['value'] == 'Breakout' else float(row['value'])
                        results.append({
                            "keyword": row['query'],
                            "score": score,
                            "type": "rising",
                            "source": "google_trends",
                            "timestamp": datetime.now().isoformat()
                        })
                        seen_keywords.add(kw)
            
            # Top queries
            top = data[key].get("top")
            if top is not None and not top.empty:
                for _, row in top.iterrows():
                    kw = row['query'].lower().strip()
                    if kw not in seen_keywords:
                        results.append({
                            "keyword": row['query'],
                            "score": float(row['value']),
                            "type": "top",
                            "source": "google_trends",
                            "timestamp": datetime.now().isoformat()
                        })
                        seen_keywords.add(kw)
        
        if len(results) == 0:
            print("⚠️ Empty results — using fallback")
            return fallback_interest(pytrends, keywords, cache_key)
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Cache the results
        save_to_cache(cache_key, results)
        
        print(f"✅ Google Trends: {len(results)} keywords fetched")
        return results
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Google Trends Error: {error_msg[:200]}")
        
        # If rate limited, try to use cache
        if "429" in error_msg or "rate" in error_msg.lower():
            cached = get_cached_results(cache_key, max_age_hours=24)
            if cached:
                print("✅ Using cached data due to rate limit")
                return cached
        
        return []


def fallback_interest(pytrends, keywords, cache_key):
    """Fallback to interest_over_time when related_queries fails"""
    try:
        print("🔄 Trying fallback method (interest_over_time)...")
        
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            print("❌ Fallback also failed - no data")
            return []
        
        last = df.iloc[-1]
        results = []
        
        for kw in keywords:
            score = float(last.get(kw, 0))
            if score > 0:
                results.append({
                    "keyword": kw,
                    "score": score,
                    "type": "interest",
                    "source": "google_trends_fallback",
                    "timestamp": datetime.now().isoformat()
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Cache fallback results too
        save_to_cache(cache_key, results)
        
        print(f"✅ Fallback successful: {len(results)} keywords")
        return results
    
    except Exception as e:
        print(f"❌ Fallback error: {str(e)[:100]}")
        return []


def get_trending_topics(geo="IN"):
    """Get Google's current trending searches (lightweight, less rate limited)"""
    cache_key = f"trending_topics_{geo}"
    
    # Check cache first (30 min expiry for trending)
    if True:  # Always use cache for trending to avoid rate limits
        cached = get_cached_results(cache_key, max_age_hours=0.5)
        if cached:
            return cached
    
    try:
        pytrends = TrendReq(
            hl="en-US",
            tz=330,
            requests_args={"headers": {"User-Agent": random.choice(USER_AGENTS)}}
        )
        
        trending = pytrends.trending_searches(pn=geo.lower())
        results = []
        
        # Education-related keywords
        edu_keywords = [
            'exam', 'result', 'admission', 'course', 'university', 
            'college', 'school', 'education', 'student', 'study',
            'test', 'entrance', 'scholarship', 'degree', 'learning',
            'jee', 'neet', 'upsc', 'gate', 'cat', 'gre', 'ielts'
        ]
        
        for idx, keyword in enumerate(trending[0]):
            # Filter for education-related terms
            if any(term in keyword.lower() for term in edu_keywords):
                results.append({
                    "keyword": keyword,
                    "score": 100 - idx,
                    "type": "trending",
                    "source": "google_trending",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Cache the results
        save_to_cache(cache_key, results)
        
        print(f"✅ Trending topics: {len(results)} education-related")
        return results
    
    except Exception as e:
        print(f"❌ Trending topics error: {str(e)[:100]}")
        return []


def save_results(results, filename=None):
    """Save results to JSON file"""
    if filename is None:
        filename = f"google_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_keywords': len(results)
            },
            'keywords': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Results saved to {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🚀 GOOGLE TRENDS TRACKER (Rate-Limited)")
    print("="*70)
    
    # Fetch with caching enabled (1 hour cache)
    results = fetch_google_trends(
        geo="IN",
        timeframe="now 1-d",
        use_cache=True,
        cache_hours=1
    )
    
    if results:
        print(f"\n📊 Top 20 Keywords:")
        print(f"{'#':<4} {'Keyword':<40} {'Score':<10} {'Type'}")
        print("-" * 70)
        
        for i, item in enumerate(results[:20], 1):
            print(f"{i:<4} {item['keyword']:<40} {item['score']:<10.1f} {item['type']}")
        
        # Save results
        save_results(results)
        
        print("\n✅ Google Trends scraping complete!")
        print("\n💡 TIP: Data is cached for 1 hour to avoid rate limits.")
        print("💡 Run again within 1 hour to use cached data instantly.\n")
    else:
        print("\n⚠️ No results. Try again in a few minutes.\n")