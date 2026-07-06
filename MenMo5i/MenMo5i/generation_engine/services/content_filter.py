import re

# Terms that are blocked entirely
BLOCKED_WORDS = set([
    # Violence / gore
    "gore", "blood", "murder", "kill", "corpse", "dead body", "decapitation",
    "torture", "execution", "suicide", "self-harm", "cutting", "mutilation",
    "cannibalism", "massacre", "genocide", "terror", "mass shooting",
    # Hate speech
    "nazi", "swastika", "kkk", "white supremacy", "racial slur", "racist",
    # NSFW / explicit — aggressive blocking
    "nude", "naked", "sex", "porn", "explicit", "nsfw", "erotic", "xxx",
    "hentai", "rule34", "sexual", "pornographic", "gross", "gaping",
    "nsfw", "milf", "bikini", "lingerie", "underwear", "swimsuit",
    "cleavage", "boobs", "tits", "ass", "butt", "thong", "stripper",
    "stripping", "strip club", "voyeur", "fetish", "bdsm", "kink",
    "masturbat", "orgasm", "cum", "semen", "penis", "vagina", "dildo",
    "prostitut", "escort", "hooker", "camgirl", "onlyfans",
    "anime girl", "waifu", "thicc", "sexy", "hot girl", "hot woman",
    "seductive", "sultry", "provocative", "sensual", "risque",
    "playboy", "penthouse", "topless", "bottomless", "bare chest",
    "torso", "navel", "midriff", "belly button", "see-through",
    "wet t-shirt", "wet look", "bondage", "domination",
    "lolita", "shota", "cub", "young girl", "young boy", "minor",
    # Drugs / illegal
    "cocaine", "heroin", "meth", "crack", "inject", "needle drug",
    # Prohibited symbols
    "isis", "taliban", "cartel",
])

# Terms that flag a prompt for review (borderline content)
FLAGGED_WORDS = set([
    "weapon", "gun", "rifle", "pistol", "knife", "sword", "axe",
    "skull", "skeleton", "demon", "devil", "satanic", "occult",
    "alcohol", "beer", "wine", "liquor", "cigarette", "smoke",
    "drug", "weed", "marijuana", "cannabis",
    "aggressive", "violent", "war", "battle", "attack",
])


def check_prompt(prompt: str) -> dict:
    """
    Check a prompt for inappropriate content.
    Returns {'allowed': bool, 'reason': str, 'flagged': bool}
    """
    lower = prompt.lower()

    for word in BLOCKED_WORDS:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, lower):
            return {
                'allowed': False,
                'reason': f'Blocked term detected: "{word}"',
                'flagged': False,
            }

    flagged_words = []
    for word in FLAGGED_WORDS:
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, lower):
            flagged_words.append(word)

    return {
        'allowed': True,
        'reason': '',
        'flagged': bool(flagged_words),
        'flagged_words': flagged_words,
    }
