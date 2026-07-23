import json
import os

CACHE_FILE = "cache/research_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(company, research_data):
    os.makedirs('cache', exist_ok=True)
    cache = load_cache()
    cache[company] = research_data
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

def get_cached_research(company):
    return load_cache().get(company)