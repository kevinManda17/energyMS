from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DailyReportView, DataExportViewSet, ExportCsvView

router = DefaultRouter()
router.register("reports/exports", DataExportViewSet, basename="data-export")

urlpatterns = [
    path("reports/daily/", DailyReportView.as_view(), name="reports-daily"),
    path(
        "reports/export/csv/",
        ExportCsvView.as_view(),
        name="reports-export-csv",
    ),
] + router.urls

