from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Dataset
from .serializers import DatasetSerializer
from .services import load_dataframe, validate_and_clean


class DatasetViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/datasets/          list imported datasets
    POST /api/datasets/import/   upload + validate a CSV/JSON dataset
    """

    serializer_class = DatasetSerializer
    queryset = Dataset.objects.all()
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["kind", "status"]

    @action(detail=False, methods=["post"], url_path="import")
    def import_dataset(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dataset = serializer.save(uploaded_by=request.user)

        try:
            df = load_dataframe(dataset.file)
            ok, message, _cleaned, columns = validate_and_clean(
                df, dataset.kind
            )
        except Exception as exc:  # noqa: BLE001 - report any parse error
            ok, message, columns = False, f"Erreur de lecture: {exc}", []
            df = None

        dataset.status = Dataset.Status.VALID if ok else Dataset.Status.INVALID
        dataset.message = message
        dataset.columns = columns
        dataset.rows = int(len(df)) if df is not None else 0
        dataset.save()

        return Response(
            self.get_serializer(dataset).data,
            status=status.HTTP_201_CREATED if ok else status.HTTP_400_BAD_REQUEST,
        )
