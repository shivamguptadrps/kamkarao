from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView
from django.views.static import serve

from apps.accounts import views as acc
from apps.ads import views as ads
from apps.core import views as core
from apps.core.admin_views import dashboard, private_file
from apps.core.sitemaps import SITEMAPS
from apps.leads import views as leads
from apps.providers import views as prov


urlpatterns = [
    path("admin/dashboard/", admin.site.admin_view(dashboard), name="admin_dashboard"),
    path("admin/private/<path:name>", admin.site.admin_view(private_file), name="admin_private_file"),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("ad/<int:pk>/", ads.banner_click, name="banner_click"),
    path("robots.txt", core.robots),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("sw.js", TemplateView.as_view(template_name="sw.js", content_type="application/javascript")),
    path("manifest.webmanifest", TemplateView.as_view(template_name="manifest.webmanifest",
                                                     content_type="application/manifest+json")),
]

urlpatterns += i18n_patterns(
    path("", core.home, name="home"),
    path("search/", core.search, name="search"),
    path("area/", core.area_sheet, name="area_sheet"),
    path("area/set/", core.area_set, name="area_set"),
    path("area/nearest/", core.area_nearest, name="area_nearest"),
    path("offline/", core.offline, name="offline"),
    path("credits/", core.credits, name="credits"),
    path("p/<int:pk>-<slug:slug>/", prov.provider_detail, name="provider_detail"),
    path("p/<int:pk>/reveal/", prov.reveal, name="provider_reveal"),
    path("p/<int:pk>/complaint/", prov.complaint, name="provider_complaint"),
    path("join/", prov.join, name="join"),
    path("kaam-batao/", leads.work_request, name="work_request"),
    path("r/<str:token>/", leads.rate, name="rate"),
    path("login/", acc.login_sheet, name="login_sheet"),
    path("login/otp/", acc.otp_send, name="otp_send"),
    path("login/verify/", acc.otp_verify, name="otp_verify"),
    path("logout/", acc.logout_view, name="logout"),
    path("account/", acc.account, name="account"),
    path("<slug:city_slug>/<slug:slug>/", core.category_list, name="category_list"),
    prefix_default_language=True,
)

if settings.DEBUG or not settings.S3_BUCKET:
    # Public media from disk. On a real server put Nginx/Caddy (or R2) in front instead.
    urlpatterns += [path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT})]
