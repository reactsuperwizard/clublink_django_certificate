from rest_framework import status, views
from rest_framework.response import Response


class PingView(views.APIView):
    def get(self, request, format=None):
        return Response(status=status.HTTP_200_OK)
