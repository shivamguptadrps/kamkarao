"""Base data for Banda: real mohallas and the launch services.

Mohalla points are approximate centres taken from public map listings (October 2026).
Check each one in Admin → Mohallas → "Open map" and drag to the right spot if needed.
"""

CITY = {"slug": "banda", "name_en": "Banda", "name_hi": "बांदा", "lat": 25.4763, "lon": 80.3395}

# (slug, English, Hindi, lat, lon)
AREAS = [
    ("civil-lines", "Civil Lines", "सिविल लाइंस", 25.4867, 80.3338),
    ("swaraj-colony", "Swaraj Colony", "स्वराज कॉलोनी", 25.4857, 80.3313),
    ("awas-vikas", "Awas Vikas Colony", "आवास विकास कॉलोनी", 25.4903, 80.3382),
    ("sarvodaya-nagar", "Sarvodaya Nagar", "सर्वोदय नगर", 25.5003, 80.3408),
    ("indira-nagar", "Indira Nagar", "इंदिरा नगर", 25.4890, 80.3464),
    ("kashiram-colony", "Kashiram Colony", "कांशीराम कॉलोनी", 25.4940, 80.3417),
    ("jaraili-kothi", "Jaraili Kothi", "जरैली कोठी", 25.4944, 80.3294),
    ("bangalipura", "Bangalipura", "बंगालीपुरा", 25.4812, 80.3394),
    ("kalu-kuan", "Kalu Kuan", "कालू कुआं", 25.4792, 80.3404),
    ("katra", "Katra", "कटरा", 25.4773, 80.3255),
    ("balkhandi-naka", "Balkhandi Naka", "बलखंडी नाका", 25.4751, 80.3309),
    ("chhawani", "Chhawani", "छावनी", 25.4745, 80.3356),
    ("pili-kothi", "Pili Kothi", "पीली कोठी", 25.4769, 80.3356),
    ("gular-naka", "Gular Naka", "गूलर नाका", 25.4718, 80.3366),
    ("mardan-naka", "Mardan Naka", "मर्दन नाका", 25.4701, 80.3343),
    ("chhoti-bazar", "Chhoti Bazar", "छोटी बाज़ार", 25.4689, 80.3311),
    ("khinni-naka", "Khinni Naka", "खिन्नी नाका", 25.4676, 80.3302),
    ("khutla", "Khutla", "खुटला", 25.4690, 80.3262),
    ("aliganj", "Aliganj", "अलीगंज", 25.4636, 80.3394),
    ("bhuragarh", "Bhuragarh", "भूरागढ़", 25.4791, 80.3100),
]

# slug, en, hi, icon key, sort, tagline en, tagline hi, subs [(en, hi)], rates [(en, hi, price, unit_en, unit_hi)]
CATEGORIES = [
    ("electrician", "Electrician", "इलेक्ट्रीशियन", "electrician", 1,
     "Fans, wiring, inverter", "पंखा, वायरिंग, इन्वर्टर",
     [("Fan & lights", "पंखा / लाइट"), ("Wiring", "वायरिंग"), ("Inverter & battery", "इन्वर्टर / बैटरी"),
      ("Motor & submersible", "मोटर / समरसेबल")],
     [("Fan fitting", "पंखा फिटिंग", 150, "", ""), ("Switchboard repair", "स्विच बोर्ड ठीक करना", 100, "", ""),
      ("New wiring", "नई वायरिंग", 250, "point", "पॉइंट"), ("Inverter installation", "इन्वर्टर लगाना", 400, "", "")]),
    ("plumber", "Plumber", "प्लम्बर", "plumber", 2,
     "Taps, leaks, tanks", "नल, लीकेज, टंकी",
     [("Taps & leaks", "नल / लीकेज"), ("Water tank", "पानी की टंकी"), ("Motor fitting", "मोटर फिटिंग"),
      ("Bathroom fitting", "बाथरूम फिटिंग")],
     [("Tap replacement", "नल बदलना", 120, "", ""), ("Leak repair", "लीकेज ठीक करना", 200, "", ""),
      ("Tank cleaning", "टंकी की सफाई", 500, "", ""), ("Motor fitting", "मोटर फिटिंग", 400, "", "")]),
    ("appliance-repair", "AC · Fridge · RO", "AC · फ्रिज · RO", "appliance", 3,
     "Service and repair at home", "घर पर सर्विस और रिपेयर",
     [("AC service", "AC सर्विस"), ("Fridge", "फ्रिज"), ("RO water purifier", "RO"), ("Washing machine", "वॉशिंग मशीन")],
     [("AC service", "AC सर्विस", 450, "", ""), ("Fridge check-up", "फ्रिज चेकअप", 250, "", ""),
      ("RO service", "RO सर्विस", 350, "", ""), ("AC gas refill", "AC गैस भरना", 2200, "", "")]),
    ("bike-mechanic", "Bike mechanic", "बाइक मैकेनिक", "bike", 4,
     "Service, puncture, engine", "सर्विस, पंचर, इंजन",
     [("General service", "जनरल सर्विस"), ("Puncture", "पंचर"), ("Engine work", "इंजन का काम"),
      ("Service at home", "घर पर सर्विस")],
     [("Puncture", "पंचर", 60, "", ""), ("General service", "जनरल सर्विस", 350, "", ""),
      ("Chain set change", "चेन सेट बदलना", 200, "", ""), ("Clutch plate work", "क्लच प्लेट का काम", 450, "", "")]),
    ("carpenter", "Carpenter", "बढ़ई", "carpenter", 5,
     "Doors, locks, furniture", "दरवाज़ा, ताला, फर्नीचर",
     [("Doors & locks", "दरवाज़ा / ताला"), ("Furniture repair", "फर्नीचर मरम्मत"), ("New furniture", "नया फर्नीचर")],
     [("Door lock fitting", "दरवाज़े का ताला लगाना", 200, "", ""), ("Bed repair", "पलंग की मरम्मत", 400, "", ""),
      ("Wardrobe making", "अलमारी बनाना", 900, "sq ft", "वर्ग फुट")]),
    ("beautician", "Beautician · Mehndi", "ब्यूटीशियन · मेहंदी", "beauty", 6,
     "At home, by women", "घर पर, महिलाओं द्वारा",
     [("Threading & facial", "थ्रेडिंग / फेशियल"), ("Bridal makeup", "ब्राइडल मेकअप"), ("Mehndi", "मेहंदी")],
     [("Threading", "थ्रेडिंग", 30, "", ""), ("Facial", "फेशियल", 400, "", ""),
      ("Mehndi (both hands)", "मेहंदी (दोनों हाथ)", 500, "", ""), ("Bridal makeup", "ब्राइडल मेकअप", 5000, "", "")]),
    ("painter", "Painter", "पेंटर", "painter", 7,
     "Whitewash, paint, putty", "पुताई, पेंट, पुट्टी",
     [("House painting", "घर की पुताई"), ("Putty", "पुट्टी"), ("Waterproofing", "वॉटरप्रूफिंग")],
     [("Distemper", "डिस्टेम्पर", 8, "sq ft", "वर्ग फुट"), ("Plastic paint", "प्लास्टिक पेंट", 14, "sq ft", "वर्ग फुट"),
      ("Putty", "पुट्टी", 10, "sq ft", "वर्ग फुट")]),
]
