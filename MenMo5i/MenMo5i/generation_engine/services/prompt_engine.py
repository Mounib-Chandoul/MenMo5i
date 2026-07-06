import re

QUALITY_TAGS = [
    "flat vector illustration",
    "bold graphic lines",
    "high contrast",
    "clean composition",
    "t-shirt print design",
]

NEGATIVE_PROMPT = (
    "photo, realistic, 3d render, low quality, blurry, distorted, deformed, "
    "ugly, bad anatomy, watermark, text, signature, frame, border, "
    "complex background, messy, noisy, grainy, oversaturated, undersaturated"
)

THEME_EXPANSIONS = {
    "skull": "intricate sugar skull with ornate floral details, mexican da de muertos style",
    "death": "memento mori gothic illustration, detailed ornamental patterns, dark romantic aesthetic",
    "dark": "dark atmospheric design, high contrast shadow work, moody monochrome composition",
    "flower": "detailed botanical illustration, layered petals, organic flowing forms, nature precision",
    "nature": "lush natural elements, organic flowing shapes, botanical precision, earth tones",
    "plant": "detailed botanical engraving, leaves and vines, biophilic design, organic patterns",
    "dragon": "majestic dragon, east asian artistic influence, serpentine curves, intricate scales",
    "lion": "regal lion portrait, detailed mane, powerful stance, african savanna aesthetic",
    "eagle": "majestic eagle in flight, detailed feathers, american traditional tattoo style",
    "wolf": "stylized wolf howling at moon, geometric linework, wilderness aesthetic",
    "snake": "elegant coiled serpent, sleek minimalist lines, nature symbolism, clean curves",
    "rose": "detailed rose bloom with layered petals, gothic romantic style, thorned stem",
    "geometric": "precise sacred geometry composition, symmetrical patterns, mathematical precision, mandala influence",
    "abstract": "fluid abstract forms, modern art composition, gestural shapes, contemporary design",
    "pattern": "intricate repeating seamless pattern, detailed motifs, ornate texture, tessellation",
    "cyberpunk": "cyberpunk neon aesthetic, futuristic tech elements, vibrant electric colors, digital art style",
    "minimal": "minimalist design philosophy, zen simplicity, clean lines, elegant negative space",
    "vintage": "vintage retro aesthetic, distressed texture, nostalgic color palette, classic timeless style",
    "tribal": "tribal pattern design, bold black motifs, polynesian influence, cultural geometric patterns",
    "neon": "neon glow aesthetic, vibrant electric colors, dark background, luminous futuristic effect",
    "graffiti": "graffiti street art style, spray paint texture, urban culture, wild style lettering",
    "samurai": "samurai warrior illustration, japanese woodblock print style, detailed armor, ukiyo-e influence",
    "japanese": "japanese art style, ukiyo-e influence, traditional motifs, wave patterns, cherry blossoms",
    "egyptian": "ancient egyptian motifs, pharaoh iconography, hieroglyphic patterns, pyramid geometry",
    "celtic": "celtic knotwork design, interwoven patterns, trinity motifs, spiral details, ancient symbolism",
    "space": "cosmic space theme, stars and nebulae, deep astronomy, celestial bodies, galaxy colors",
    "ocean": "ocean themed design, wave patterns, marine life, deep blue palette, fluid motion",
    "fire": "flame design, dynamic fire shapes, warm color palette, energy and movement composition",
    "moon": "crescent moon design, lunar phases, night sky aesthetic, celestial geometry",
    "sun": "radiant sun design, solar flare patterns, warm golden palette, ray motifs",
    "star": "star pattern design, celestial motifs, constellation mapping, night sky geometry",
    "heart": "heart motif design, anatomical or stylized, love symbolism, bold central composition",
    "crown": "crown illustration, royal motifs, regal symbolism, jeweled details, monarchy theme",
    "eye": "all-seeing eye design, mystical symbolism, geometric eye, occult aesthetic, third eye",
    "hand": "hand illustration, mudra or gesture, detailed linework, symbolic hand poses",
    "feather": "feather illustration with delicate details, bird motifs, bohemian aesthetic, natural forms",
    "arrow": "arrow design, directional motifs, minimalist geometry, wayfinding symbols",
    "mountain": "mountain landscape design, peak silhouettes, outdoor adventure, nature geometry",
    "forest": "forest scene design, tree silhouettes, woodland aesthetic, nature immersion",
    "city": "cityscape design, skyline silhouette, urban landscape, architectural geometry",
    "compass": "compass design, navigation motifs, exploration theme, nautical geometry",
    "key": "vintage key illustration, mystery symbolism, lock and key motifs, ornate details",
    "anchor": "anchor design, nautical theme, maritime motifs, sailor style, rope details",
    "cross": "cross design, ornamental details, faith symbolism, gothic or simple style",
    "mandala": "mandala design, concentric patterns, spiritual geometry, meditative symmetry, intricate details",
    "wave": "japanese wave pattern, fluid motion lines, ocean movement, traditional japanese art style",
    "cloud": "cloud design, atmospheric shapes, ethereal forms, sky aesthetic, floating composition",
    "tree": "tree of life design, branching patterns, roots and leaves, nature symbolism, organic growth",
    "lotus": "lotus flower design, spiritual symbolism, buddhist influence, blooming petals, sacred geometry",
    "phoenix": "phoenix rising illustration, rebirth symbolism, fiery wings, mythological bird, flames",
    "tiger": "tiger illustration, fierce expression, striped patterns, power symbolism, wildlife art",
    "panther": "black panther design, sleek silhouette, jungle aesthetic, powerful stance, wildlife",
    "bear": "bear illustration, wilderness theme, powerful form, forest animal, wildlife art",
    "horse": "horse design, galloping silhouette, equestrian theme, freedom symbolism, movement",
    "owl": "owl illustration, wisdom symbolism, detailed feathers, nocturnal aesthetic, wise eyes",
    "raven": "raven design, dark aesthetic, detailed feathers, gothic symbolism, corvid details",
    "butterfly": "butterfly design, symmetrical wings, delicate details, transformation symbolism, nature art",
    "bee": "bee illustration, hexagonal patterns, nature details, pollination theme, geometric wings",
    "scorpion": "scorpion design, arachnid details, desert aesthetic, curved tail, exoskeleton pattern",
    "spider": "spider design, web patterns, arachnid details, gothic style, symmetry",
    "dagger": "dagger design, blade illustration, medieval aesthetic, ornate handle, sharp lines",
    "axe": "battle axe design, viking aesthetic, norse mythology, weapon illustration, tribal patterns",
    "shield": "shield design, heraldic motifs, protection symbolism, medieval aesthetic, crest patterns",
    "helmet": "helmet illustration, spartan or viking style, warrior aesthetic, battle-ready design",
    "crystal": "crystal design, geometric facets, gemstone aesthetic, prismatic colors, mineral shapes",
    "diamond": "diamond design, faceted geometry, jewel aesthetic, luxury symbolism, sparkling edges",
    "skate": "skateboarding design, skate culture, street aesthetic, ollie silhouette, board graphics",
    "music": "music themed design, note patterns, audio wave forms, rhythmic composition, concert aesthetic",
    "guitar": "guitar illustration, rock aesthetic, musical instrument, electric or acoustic, strings details",
    "vinyl": "vinyl record design, music nostalgia, retro aesthetic, album art style, turntable culture",
    "camera": "camera illustration, photography theme, vintage or modern style, lens details, shutter motifs",
    "map": "map design, cartography aesthetic, compass elements, route lines, exploration theme",
    "globe": "globe design, world map, travel theme, continents, earth illustration, exploration",
    "robot": "robot illustration, futuristic design, mechanical details, sci-fi aesthetic, tech patterns",
    "alien": "alien design, extraterrestrial theme, ufo motifs, space invaders style, sci-fi graphics",
    "ufo": "ufo design, flying saucer, alien spacecraft, beam of light, night sky, sci-fi theme",
    "castle": "castle illustration, medieval architecture, fortress design, fantasy theme, turret details",
    "crown": "crown design, royal motifs, jeweled details, king or queen theme, regal symbols",
    "mask": "mask design, masquerade theme, theatrical aesthetic, venetian style, ornate details",
    "skateboard": "skateboard deck design, street culture, board graphics, ollie trick silhouette",
    "surf": "surf culture design, wave riding, beach aesthetic, ocean lifestyle, surfboard shapes",
    "skull": "intricate skull illustration, mexican sugar skull style, decorative patterns, ornate details",
}

STYLE_SUFFIXES = {
    "cyberpunk": "cyberpunk aesthetic, neon colors, dark background, futuristic tech patterns, digital glitch effects",
    "minimal": "minimalist style, clean lines, simple shapes, negative space, monochrome palette, elegant",
    "vintage": "vintage retro style, distressed look, 80s aesthetic, faded colors, nostalgic feel",
    "tribal": "tribal patterns, geometric shapes, african inspired motifs, bold symmetrical designs",
    "neon": "neon glow style, vibrant bright colors, glowing outlines, dark background, electric atmosphere",
    "graffiti": "graffiti street art style, spray paint texture, wild style lettering, urban culture",
    "abstract": "abstract geometric art, fluid shapes, gradient colors, modern art composition",
}

CATEGORY_PREFIXES = {
    "abstract": "Abstract geometric composition, fluid shapes, modern art inspired",
    "typography": "Bold typography and lettering design, custom font treatment, text-based graphic",
    "illustration": "Detailed vector illustration design, artistic composition, rich visual narrative",
    "techwear": "Techwear futuristic graphic design, cyberpunk aesthetic, neon accents, tech patterns",
    "minimal": "Minimalist clean design, simple shapes, elegant negative space, zen aesthetic",
}


def detect_themes(prompt: str) -> dict[str, str]:
    """Detect which themes are present in the prompt and return their expansions."""
    lower = prompt.lower()
    matches = {}
    for keyword, expansion in THEME_EXPANSIONS.items():
        if keyword in lower:
            matches[keyword] = expansion
    return matches


def enhance_prompt(
    prompt: str,
    category: str = "",
    style: str = "",
) -> str:
    """
    Expand a raw user prompt into a detailed, high-quality prompt
    optimized for T-shirt design text-to-image generation.

    Combines theme-based expansions (from keyword detection),
    category-specific prefixes, style suffixes, and quality tags.
    """
    themes = detect_themes(prompt)
    theme_desc = "; ".join(themes.values()) if themes else ""

    parts = []

    if category and category in CATEGORY_PREFIXES:
        parts.append(CATEGORY_PREFIXES[category])

    if theme_desc:
        parts.append(theme_desc)
    else:
        parts.append(prompt)

    if style and style in STYLE_SUFFIXES and STYLE_SUFFIXES[style]:
        parts.append(STYLE_SUFFIXES[style])

    parts.extend(QUALITY_TAGS)

    return ", ".join(parts)
