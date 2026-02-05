"""
Job-resume match scoring algorithm.
Scores jobs 0-100 based on keyword match, location, experience level, and description quality.
"""
import logging

logger = logging.getLogger(__name__)

# Core skills get higher weight (5 pts), secondary skills get 3 pts
CORE_SKILLS = {
    'python', 'django', 'react', 'typescript', 'javascript', 'next.js',
    'postgresql', 'docker', 'aws', 'claude', 'anthropic', 'llm', 'ai',
    'machine learning', 'drf', 'rest api', 'rest apis',
}

AI_TERMS = {
    'ai', 'artificial intelligence', 'machine learning', 'ml', 'llm',
    'large language model', 'claude', 'anthropic', 'openai', 'gpt',
    'ai native', 'ai-native', 'generative ai', 'gen ai',
    'natural language processing', 'nlp', 'deep learning',
}


def score_job_for_user(listing, resume_data: dict, preferences) -> dict:
    """
    Score a job listing against user's resume and preferences.
    Returns {score: int, breakdown: dict, matched_keywords: list}
    """
    score = 0
    breakdown = {}
    matched = []

    title_lower = (listing.get('title', '') or '').lower()
    desc_lower = (listing.get('description', '') or '').lower()
    location_lower = (listing.get('location', '') or '').lower()
    combined = f"{title_lower} {desc_lower}"

    # 1. Skill keyword match (0-40 points)
    user_skills = [s.lower() for s in resume_data.get('skills', [])]
    keyword_points = 0
    for skill in user_skills:
        if skill in combined:
            pts = 5 if skill in CORE_SKILLS else 3
            keyword_points += pts
            matched.append(skill)

    # Also check preference keywords (title matches worth more)
    for kw in (preferences.keywords or []):
        kw_lower = kw.lower()
        if kw_lower not in [m.lower() for m in matched]:
            if kw_lower in title_lower:
                keyword_points += 8  # Title match = strong signal
                matched.append(kw)
            elif kw_lower in desc_lower:
                keyword_points += 4
                matched.append(kw)

    keyword_score = min(40, keyword_points)
    score += keyword_score
    breakdown['keyword_match'] = keyword_score

    # 2. AI/ML relevance bonus (0-15 points)
    ai_score = 0
    ai_hits = sum(1 for term in AI_TERMS if term in combined)
    if ai_hits >= 3:
        ai_score = 15
    elif ai_hits >= 2:
        ai_score = 10
    elif ai_hits >= 1:
        ai_score = 5
    score += ai_score
    breakdown['ai_relevance'] = ai_score

    # 3. Excluded keyword penalty
    for excluded in (preferences.excluded_keywords or []):
        if excluded.lower() in combined:
            score -= 20
            breakdown['excluded_penalty'] = -20
            break

    # 4. Location match (0-15 points)
    pref_location = (preferences.location or '').lower()
    location_score = 0
    if pref_location in location_lower:
        location_score = 15
    elif 'remote' in location_lower or 'anywhere' in location_lower:
        location_score = 12 if preferences.remote_ok else 5
    elif 'canada' in location_lower or 'ontario' in location_lower:
        location_score = 8
    score += location_score
    breakdown['location_match'] = location_score

    # 5. Experience level match (0-15 points) - favor junior/entry level
    exp_score = 0
    if 'junior' in title_lower or 'entry' in title_lower or 'jr' in title_lower:
        exp_score = 15  # Best match for junior roles
    elif 'intern' in title_lower:
        exp_score = 10
    elif 'mid' in title_lower or '3+' in combined or '3 years' in combined:
        exp_score = 12
    elif 'senior' in title_lower or '5+' in combined or '5 years' in combined:
        exp_score = 5  # Still acceptable but not preferred
    elif 'staff' in title_lower or 'principal' in title_lower or 'lead' in title_lower:
        exp_score = 3  # Too senior
    else:
        exp_score = 10  # Neutral - likely open to various levels
    score += exp_score
    breakdown['experience_match'] = exp_score

    # 6. Description quality (0-15 points)
    quality_score = 0
    desc = listing.get('description', '') or ''
    if len(desc) > 200:
        quality_score += 5  # Has substantial description
    core_tech_in_desc = sum(1 for t in ['django', 'react', 'python', 'typescript', 'next.js', 'postgresql'] if t in desc_lower)
    quality_score += min(10, core_tech_in_desc * 3)
    score += quality_score
    breakdown['description_quality'] = quality_score

    # Clamp to 0-100
    score = max(0, min(100, score))

    return {
        'score': score,
        'breakdown': breakdown,
        'matched_keywords': matched,
    }
