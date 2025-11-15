#!/usr/bin/env python3
"""Fix occasion detection to prioritize context"""

with open('app/routers/suggestions.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update OCCASION_KEYWORDS to be more context-aware
old_occasions = '''OCCASION_KEYWORDS = {
    "formal": {"formal", "wedding", "ceremony", "black tie", "reception"},
    "business": {"business", "office", "interview", "meeting", "work"},
    "smart casual": {"smart", "smart casual", "semi-formal"},
    "party": {"party", "night out", "club", "birthday", "celebration"},
    "casual": {"casual", "hangout", "weekend", "everyday", "relaxed", "any"},
}'''

new_occasions = '''OCCASION_KEYWORDS = {
    "formal": {"formal", "wedding", "ceremony", "black tie", "reception", "gala"},
    "business": {"business", "office", "interview", "corporate", "professional"},
    "smart casual": {"smart", "smart casual", "semi-formal", "upscale"},
    "party": {"party", "night out", "club", "birthday", "celebration", "cocktail"},
    "casual": {"casual", "hangout", "weekend", "everyday", "relaxed", "any", "coffee", "brunch", "errands", "comfortable"},
}'''

content = content.replace(old_occasions, new_occasions)

# Update _detect_occasion to handle context better
old_detect = '''def _detect_occasion(tokens: List[str]) -> str:
    token_set = set(tokens)
    for name, keys in OCCASION_KEYWORDS.items():
        if token_set & keys:
            return name
    # default
    return "casual"'''

new_detect = '''def _detect_occasion(tokens: List[str]) -> str:
    token_set = set(tokens)
    
    # Check for explicit casual keywords first (higher priority)
    if token_set & OCCASION_KEYWORDS["casual"]:
        return "casual"
    
    # Then check other occasions
    for name, keys in OCCASION_KEYWORDS.items():
        if name != "casual" and token_set & keys:
            return name
    
    # default
    return "casual"'''

content = content.replace(old_detect, new_detect)

with open('app/routers/suggestions.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed occasion detection!")
