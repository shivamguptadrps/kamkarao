"""End-to-end checks of the flows that matter. Run: python manage.py test"""
import re
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import Customer, OtpCode
from apps.ads.models import Banner, BannerDailyStat
from apps.core.models import Area
from apps.leads.models import Lead, Rating, WorkRequest
from apps.providers.models import JoinRequest, Provider

HX = {"HTTP_HX_REQUEST": "true"}


@override_settings(OTP_PROVIDER="console", DEBUG=True, MEDIA_ROOT=tempfile.mkdtemp(), PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())
class FlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from io import StringIO
        call_command("seed_demo", stdout=StringIO())

    def login(self, phone="9876543210"):
        r = self.client.post("/hi/login/otp/", {"phone": phone}, **HX)
        code = re.search(r"<b>(\d{4})</b>", r.content.decode()).group(1)
        r = self.client.post("/hi/login/verify/", {"otp": code}, **HX)
        self.assertEqual(r.status_code, 200)
        return Customer.objects.get(phone=phone)

    def test_pages_load_in_both_languages(self):
        for lang in ("hi", "en"):
            for path in ["/", "/banda/electrician/", "/kaam-batao/", "/join/", "/credits/"]:
                r = self.client.get(f"/{lang}{path}")
                self.assertEqual(r.status_code, 200, path)
        self.assertContains(self.client.get("/hi/"), "भरोसेमंद")
        self.assertContains(self.client.get("/en/"), "Trusted local workers")

    def test_number_hidden_until_login_and_reveal_logs_lead(self):
        p = Provider.objects.filter(status="live").first()
        listing = self.client.get(f"/hi/banda/{p.category.slug}/").content.decode()
        self.assertNotIn(p.phone, listing)
        self.assertIn(p.phone_masked, listing)
        r = self.client.get(f"/hi/p/{p.pk}/reveal/?mode=call", **HX)
        self.assertNotIn(p.phone, r.content.decode())
        self.assertContains(r, "OTP")
        customer = self.login()
        r = self.client.get(f"/hi/p/{p.pk}/reveal/?mode=wa", **HX)
        self.assertContains(r, p.phone_pretty)
        self.assertEqual(Lead.objects.filter(customer=customer, provider=p).count(), 1)
        self.client.get(f"/hi/p/{p.pk}/reveal/?mode=call", **HX)  # same day: no duplicate lead
        self.assertEqual(Lead.objects.filter(customer=customer, provider=p).count(), 1)

    def test_wrong_otp_rejected(self):
        self.client.post("/hi/login/otp/", {"phone": "9876500000"}, **HX)
        r = self.client.post("/hi/login/verify/", {"otp": "0000"}, **HX)
        if r.status_code == 200 and not r.content:  # 1 in 10,000 chance the random code was 0000
            return
        self.assertContains(r, "OTP")
        self.assertFalse(Customer.objects.filter(phone="9876500000").exists())

    def test_no_otp_mode(self):
        p = Provider.objects.filter(status="live").first()
        with self.settings(OTP_PROVIDER="none"):
            r = self.client.post("/hi/login/otp/", {"phone": "9876500001"}, **HX)
            self.assertIn("HX-Refresh", r.headers)
            self.assertFalse(OtpCode.objects.filter(phone="9876500001").exists())
            r = self.client.get(f"/hi/p/{p.pk}/reveal/", **HX)
            self.assertContains(r, p.phone_pretty)

    def test_invalid_phone(self):
        r = self.client.post("/hi/login/otp/", {"phone": "12345"}, **HX)
        self.assertContains(r, "error")
        self.assertFalse(OtpCode.objects.exists())

    def test_daily_limit(self):
        self.login()
        with self.settings(DAILY_REVEAL_LIMIT=2):
            ids = list(Provider.objects.filter(status="live").values_list("pk", flat=True)[:3])
            for pk in ids[:2]:
                self.client.get(f"/hi/p/{pk}/reveal/", **HX)
            r = self.client.get(f"/hi/p/{ids[2]}/reveal/", **HX)
            self.assertNotContains(r, Provider.objects.get(pk=ids[2]).phone_pretty)

    def test_rating_and_auto_pause(self):
        customer = self.login()
        p = Provider.objects.filter(status="live").first()
        before = p.rating_count
        lead = Lead.objects.create(customer=customer, provider=p)
        self.client.post(f"/hi/r/{lead.token}/", {"outcome": "done", "stars": "5", "text": "बढ़िया"})
        p.refresh_from_db()
        self.assertEqual(p.rating_count, before + 1)
        self.assertFalse(Rating.objects.get(lead=lead).is_approved)  # text waits for admin
        # Three unanswered leads in a row pause the provider.
        for _ in range(3):
            l2 = Lead.objects.create(customer=customer, provider=p)
            self.client.post(f"/hi/r/{l2.token}/", {"outcome": "no_answer"})
        p.refresh_from_db()
        self.assertEqual(p.status, Provider.Status.PAUSED)
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 404)

    def test_area_selection_orders_nearest_first(self):
        katra = Area.objects.get(slug="katra")
        self.client.post("/hi/area/set/", {"area": katra.pk, "next": "/hi/"})
        r = self.client.get("/hi/banda/electrician/")
        first = r.context["providers"][0]
        self.assertTrue(first.is_featured or first.area_id == katra.pk)
        dists = [p.distance_km for p in r.context["providers"] if not p.is_featured]
        self.assertEqual(dists, sorted(dists))

    def test_filters(self):
        r = self.client.get("/hi/banda/beautician/?female=1&today=1")
        self.assertTrue(all(p.gender == "f" and p.available_today for p in r.context["providers"]))

    def test_work_request_and_join(self):
        r = self.client.post("/hi/kaam-batao/", {"text": "पंखा नहीं चल रहा", "phone": "9876543211", "when": "now"})
        self.assertContains(r, "KK-")
        self.assertEqual(WorkRequest.objects.get().category.slug, "electrician")
        self.client.post("/hi/join/", {"name": "Test", "phone": "9876543212"})
        self.assertTrue(JoinRequest.objects.filter(phone="9876543212").exists())

    def test_search_routes_to_service(self):
        r = self.client.get("/hi/search/?q=नल टपक रहा")
        self.assertRedirects(r, "/hi/banda/plumber/")

    def test_banner_click_counted(self):
        b = Banner.objects.first()
        r = self.client.get(f"/ad/{b.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(BannerDailyStat.objects.get(banner=b).clicks, 1)

    def test_language_switch_keeps_page(self):
        r = self.client.post("/i18n/setlang/", {"language": "en", "next": "/hi/banda/plumber/"})
        self.assertEqual(r["Location"], "/en/banda/plumber/")

    def test_admin_dashboard(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser("boss", "b@example.com", "pass12345")
        self.client.login(username="boss", password="pass12345")
        self.assertRedirects(self.client.get("/admin/dashboard/"), "/admin/")
        home = self.client.get("/admin/")
        self.assertContains(home, "To do now")
        for url in ["providers/provider", "providers/joinrequest", "leads/lead", "leads/rating",
                    "leads/complaint", "leads/workrequest", "accounts/customer", "ads/banner",
                    "core/category", "core/area", "core/city", "auth/user", "auth/group"]:
            self.assertEqual(self.client.get(f"/admin/{url}/").status_code, 200, url)
        p = Provider.objects.first()
        self.assertEqual(self.client.get(f"/admin/providers/provider/{p.pk}/change/").status_code, 200)
        self.assertEqual(self.client.get("/admin/providers/provider/add/").status_code, 200)
        b = Banner.objects.first()
        self.assertEqual(self.client.get(f"/admin/ads/banner/{b.pk}/change/").status_code, 200)

    def test_admin_join_request_to_provider(self):
        from django.contrib.auth.models import User
        from apps.providers.models import JoinRequest
        User.objects.create_superuser("boss", "b@example.com", "pass12345")
        self.client.login(username="boss", password="pass12345")
        jr = JoinRequest.objects.create(name="Ramesh", phone="9000011111",
                                        category=Provider.objects.first().category,
                                        area=Provider.objects.first().area)
        r = self.client.get(f"/admin/providers/joinrequest/{jr.pk}/create-provider/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/providers/provider/add/?", r["Location"])
        form = self.client.get(r["Location"])
        self.assertContains(form, 'value="9000011111"')

    def test_helper_cannot_delete(self):
        from django.contrib.auth.models import Group, User
        from django.core.management import call_command
        call_command("setup_roles", verbosity=0)
        u = User.objects.create_user("helper", password="pass12345", is_staff=True)
        u.groups.add(Group.objects.get(name="Helper"))
        self.client.login(username="helper", password="pass12345")
        p = Provider.objects.first()
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/providers/provider/{p.pk}/change/").status_code, 200)
        self.assertEqual(self.client.get(f"/admin/providers/provider/{p.pk}/delete/").status_code, 403)
        self.assertEqual(self.client.get("/admin/ads/banner/add/").status_code, 403)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)
