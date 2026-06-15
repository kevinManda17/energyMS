from rest_framework import serializers

from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = (
            "id",
            "name",
            "kind",
            "file",
            "status",
            "rows",
            "columns",
            "message",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "rows",
            "columns",
            "message",
            "created_at",
        )
