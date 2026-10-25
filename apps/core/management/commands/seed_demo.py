"""Demo providers, reviews and banners so the site looks alive on your laptop.

Everything here is MADE UP. Before launch run:  python manage.py seed_demo --clear
"""
import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Customer
from apps.ads.models import Banner
from apps.core.models import Area, Category, City
from apps.leads.models import Complaint, Lead, Rating, WorkRequest
from apps.providers.models import JoinRequest, Provider

# en name, hi name, category slug, mohalla slug, years, gender, sub indexes, range, available, featured, ratings
PROVIDERS = [
    ("Ramesh Kushwaha", "रमेश कुशवाहा", "electrician", "civil-lines", 14, "m", [0, 1, 2], "city", True, True, [5, 5, 5, 4, 5, 5, 4, 5]),
    ("Imran Ansari", "इमरान अंसारी", "electrician", "katra", 9, "m", [0, 1], "city", True, False, [5, 4, 5, 4, 5]),
    ("Santosh Yadav", "संतोष यादव", "electrician", "swaraj-colony", 6, "m", [0, 2], "nearby", False, False, [4, 4, 5, 4]),
    ("Deepak Prajapati", "दीपक प्रजापति", "electrician", "kalu-kuan", 11, "m", [1, 3], "city", True, False, [5, 5, 4, 5, 4, 5]),
    ("Rajkumar Nishad", "राजकुमार निषाद", "electrician", "indira-nagar", 4, "m", [0], "nearby", True, False, [5]),
    ("Aslam Siddiqui", "असलम सिद्दीकी", "electrician", "gular-naka", 18, "m", [1, 2, 3], "city", False, False, [5, 5, 5, 5, 4, 5, 5]),
    ("Mahesh Raikwar", "महेश रैकवार", "plumber", "aliganj", 12, "m", [0, 1, 3], "city", True, True, [5, 4, 5, 5, 5]),
    ("Sunil Verma", "सुनील वर्मा", "plumber", "sarvodaya-nagar", 7, "m", [0, 2], "city", True, False, [4, 5, 4, 4]),
    ("Mohd. Shakeel", "मो. शकील", "plumber", "bangalipura", 15, "m", [1, 2, 3], "city", False, False, [5, 4, 5, 5, 4]),
    ("Pappu Sahu", "पप्पू साहू", "plumber", "kashiram-colony", 3, "m", [0], "nearby", True, False, []),
    ("Irfan Mansoori", "इरफ़ान मंसूरी", "appliance-repair", "chhawani", 10, "m", [0, 1, 3], "city", True, True, [5, 5, 4, 5, 5, 5]),
    ("Ajay Gupta", "अजय गुप्ता", "appliance-repair", "civil-lines", 8, "m", [0, 2], "city", False, False, [4, 5, 4, 4, 5]),
    ("Dinesh Pal", "दिनेश पाल", "appliance-repair", "awas-vikas", 5, "m", [1, 2], "nearby", True, False, [4, 4, 5]),
    ("Brijesh Vishwakarma", "बृजेश विश्वकर्मा", "bike-mechanic", "pili-kothi", 16, "m", [0, 1, 2], "city", True, False, [5, 5, 4, 5, 5, 4, 5]),
    ("Salman Qureshi", "सलमान क़ुरैशी", "bike-mechanic", "balkhandi-naka", 9, "m", [0, 1], "nearby", True, False, [4, 4, 5, 4]),
    ("Ankit Yadav", "अंकित यादव", "bike-mechanic", "swaraj-colony", 5, "m", [0, 3], "city", True, False, [5, 5, 4]),
    ("Nandkishor Vishwakarma", "नंदकिशोर विश्वकर्मा", "carpenter", "khutla", 22, "m", [0, 1, 2], "city", False, False, [5, 5, 4, 5]),
    ("Lalluram Anuragi", "लल्लूराम अनुरागी", "carpenter", "indira-nagar", 13, "m", [0, 1], "city", True, False, [4, 5, 4]),
    ("Rekha Kushwaha", "रेखा कुशवाहा", "beautician", "civil-lines", 8, "f", [0, 1], "city", True, True, [5, 5, 5, 4, 5, 5]),
    ("Shabnam Bano", "शबनम बानो", "beautician", "katra", 11, "f", [1, 2], "city", True, False, [5, 4, 5, 5, 5]),
    ("Pooja Sen", "पूजा सेन", "beautician", "chhoti-bazar", 4, "f", [0, 2], "nearby", False, False, [4, 5]),
    ("Chhotelal Verma", "छोटेलाल वर्मा", "painter", "kalu-kuan", 17, "m", [0, 1, 2], "city", True, False, [5, 4, 4, 5]),
    ("Raju Painter", "राजू पेंटर", "painter", "bhuragarh", 6, "m", [0, 1], "nearby", True, False, [4, 4, 4]),
]

REVIEWS = {
    5: ["समय पर आए और काम साफ़ किया। पैसे भी वही लिए जो पहले बताए थे।",
        "फोन करते ही एक घंटे में पहुंच गए। व्यवहार बहुत अच्छा।",
        "Very good work, explained the problem properly before starting.",
        "दूसरी बार बुलाया, दोनों बार काम बढ़िया।"],
    4: ["काम अच्छा है, बस थोड़ा देर से आए।",
        "Good work. Charged a little more for material but fair."],
}

BANNERS = [
    ("Shree Ram Electricals", "home", None, "teal", "पंखे, वायर, स्विच – थोक भाव में", "Fans, wires, switches at wholesale rates",
     "छोटी बाज़ार, बांदा · घर तक डिलीवरी", "Chhoti Bazar · Home delivery", "कॉल करें", "Call now", "tel:9000000901"),
    ("Banda Sanitary House", "listing", "plumber", "indigo", "नल, पाइप, टंकी – सब एक जगह", "Taps, pipes, tanks – all in one place",
     "गूलर नाका के पास", "Near Gular Naka", "कॉल करें", "Call now", "tel:9000000902"),
    ("Ganesh Paints", "listing", "painter", "saffron", "दिवाली ऑफ़र: हर 20 लीटर पर 10% छूट", "Diwali offer: 10% off on every 20 litres",
     "कटरा रोड, बांदा", "Katra Road, Banda", "WhatsApp करें", "WhatsApp", "https://wa.me/919000000903"),
    ("Sundar Bridal Studio", "listing", "beautician", "rose", "शादी के सीज़न की बुकिंग शुरू", "Wedding season bookings open",
     "सिविल लाइंस", "Civil Lines", "बुक करें", "Book now", "tel:9000000904"),
]


class Command(BaseCommand):
    help = "Add MADE-UP providers, reviews and banners for a demo. Use --clear before going live."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Delete all providers, leads, customers, banners and requests.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["clear"]:
            for model in (Rating, Complaint, Lead, WorkRequest, JoinRequest, Banner, Provider, Customer):
                model.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Demo data removed. Mohallas and services are kept."))
            return

        call_command("seed_banda")
        rnd = random.Random(7)
        city = City.objects.get(slug="banda")
        areas = {a.slug: a for a in city.areas.all()}
        cats = {c.slug: c for c in Category.objects.all()}
        now = timezone.now()

        for i, (en, hi, cat_slug, area_slug, years, gender, subs, rng, avail, feat, ratings) in enumerate(PROVIDERS):
            cat = cats[cat_slug]
            phone = f"90000{i + 101:05d}"
            p, _ = Provider.objects.update_or_create(phone=phone, defaults=dict(
                name_en=en, name_hi=hi, gender=gender, category=cat, city=city, area=areas[area_slug],
                service_range=rng, experience_years=years, available_today=avail, is_featured=feat,
                id_type=rnd.choice(["aadhaar", "voter", "dl"]), id_last4=f"{rnd.randint(1000, 9999)}",
                phone_verified=True, consent_given=True, status=Provider.Status.LIVE,
                onboarded_by="Demo", admin_notes="DEMO DATA – made up for testing",
                bio_hi=f"{years} साल से बांदा में काम कर रहे हैं। समय पर आते हैं और काम की गारंटी देते हैं।",
                bio_en=f"Working in Banda for {years} years. Comes on time and stands by the work.",
            ))
            all_subs = list(cat.subcategories.all())
            p.subcategories.set([all_subs[j] for j in subs if j < len(all_subs)])
            p.verified_at = now - timedelta(days=rnd.randint(20, 200))
            p.save(update_fields=["verified_at"])

            # Each rating comes from a demo customer through a real lead, as in production.
            for k, stars in enumerate(ratings):
                cust, _ = Customer.objects.get_or_create(phone=f"91111{i:02d}{k:03d}")
                lead = Lead.objects.create(customer=cust, provider=p, area=rnd.choice(list(areas.values())),
                                           outcome=Lead.Outcome.DONE, followup_sent=True)
                Lead.objects.filter(pk=lead.pk).update(created_at=now - timedelta(days=rnd.randint(2, 120)))
                text = rnd.choice(REVIEWS[stars]) if stars >= 4 and k < 3 else ""
                r = Rating.objects.create(lead=lead, provider=p, stars=stars, text=text, is_approved=bool(text))
                Rating.objects.filter(pk=r.pk).update(created_at=now - timedelta(days=rnd.randint(1, 90)))
            p.jobs_done = len(ratings) + rnd.randint(0, 6)
            p.save(update_fields=["jobs_done"])

        today = timezone.localdate()
        for (shop, placement, cat_slug, theme, t_hi, t_en, s_hi, s_en, c_hi, c_en, link) in BANNERS:
            Banner.objects.update_or_create(shop_name=shop, defaults=dict(
                placement=placement, category=cats.get(cat_slug) if cat_slug else None, city=city, theme=theme,
                title_hi=t_hi, title_en=t_en, subtitle_hi=s_hi, subtitle_en=s_en, cta_hi=c_hi, cta_en=c_en,
                link=link, starts_on=today - timedelta(days=3), ends_on=today + timedelta(days=27),
                monthly_price=0, is_active=True))

        self.stdout.write(self.style.SUCCESS(
            f"Demo ready: {Provider.objects.count()} providers, {Rating.objects.count()} ratings, "
            f"{Banner.objects.count()} banners. All of it is made up – run 'seed_demo --clear' before launch."))
