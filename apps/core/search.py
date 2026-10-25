"""Map what people type ('pankha', 'नल टपक रहा', 'AC') to a service."""
from .models import Category

KEYWORDS = {
    "electrician": ["बिजली", "पंखा", "लाइट", "वायर", "स्विच", "इन्वर्टर", "मीटर", "electric", "fan", "light",
                    "wiring", "switch", "inverter", "bijli", "pankha", "motor", "submersible", "समरसेबल"],
    "plumber": ["नल", "पानी", "टंकी", "लीक", "पाइप", "बाथरूम", "tap", "plumb", "leak", "tank", "pipe",
                "nal", "tanki", "bathroom", "geyser", "गीज़र"],
    "appliance-repair": ["ac", "एसी", "फ्रिज", "fridge", "ro", "आरओ", "कूलर", "cooler", "washing",
                         "वॉशिंग", "मशीन", "refrigerator", "microwave"],
    "bike-mechanic": ["बाइक", "पंचर", "स्कूटी", "मोटरसाइकिल", "bike", "puncture", "scooty", "motorcycle",
                      "activa", "splendor", "service"],
    "carpenter": ["दरवाज़ा", "दरवाजा", "ताला", "फर्नीचर", "पलंग", "अलमारी", "बढ़ई", "door", "lock",
                  "furniture", "bed", "almirah", "carpenter", "wood", "lakdi"],
    "beautician": ["मेहंदी", "मेकअप", "फेशियल", "पार्लर", "थ्रेडिंग", "दुल्हन", "mehndi", "mehendi",
                   "makeup", "facial", "parlour", "parlor", "beauty", "bridal", "threading"],
    "painter": ["पुताई", "पेंट", "पुट्टी", "रंग", "paint", "putty", "colour", "color", "whitewash", "wall"],
}


def match_category(text: str):
    t = (text or "").lower()
    if not t:
        return None
    for slug, words in KEYWORDS.items():
        if any(w in t for w in words):
            return Category.objects.filter(slug=slug, is_active=True).first()
    for cat in Category.objects.filter(is_active=True):
        if cat.name_en.lower() in t or cat.name_hi in t:
            return cat
    return None
