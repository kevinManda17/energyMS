from django.urls import path

from .views import DailyReportView, ExportCsvView

urlpatterns = [
    path("reports/daily/", DailyReportView.as_view(), name="reports-daily"),
    path(
        "reports/export/csv/",
        ExportCsvView.as_view(),
        name="reports-export-csv",
    ),
]
