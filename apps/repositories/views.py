from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.repositories.exceptions import RepositoryError
from apps.repositories.models import Repository
from apps.repositories.serializers import (
    RepositoryCreateSerializer,
    RepositorySerializer,
    RepositorySyncSerializer,
)
from apps.repositories.services import RepositoryService


class RepositoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Repository.objects.all().order_by("-updated_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RepositoryCreateSerializer
        return RepositorySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            repository = serializer.save()
        except RepositoryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = RepositorySerializer(repository)
        return Response(output.data, status=status.HTTP_201_CREATED)


class RepositoryDetailAPIView(generics.RetrieveAPIView):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    lookup_field = "id"


class RepositorySyncAPIView(APIView):
    def post(self, request, id):
        serializer = RepositorySyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            repository = Repository.objects.get(id=id)
        except Repository.DoesNotExist:
            return Response({"detail": "Repository not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            repository = RepositoryService.sync(repository)
        except RepositoryError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = RepositorySerializer(repository)
        return Response(output.data, status=status.HTTP_200_OK)
