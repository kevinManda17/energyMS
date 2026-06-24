from rest_framework import serializers

from .models import DataExport


class DataExportSerializer(serializers.ModelSerializer):
    house_name = serializers.CharField(source="house.name", read_only=True)

    class Meta:
        model = DataExport
        fields = (
            "id",
            "user",
            "house",
            "house_name",
            "export_type",
            "start_date",
            "end_date",
            "file_path",
            "created_at",
        )
        read_only_fields = ("id", "user", "file_path", "created_at")

