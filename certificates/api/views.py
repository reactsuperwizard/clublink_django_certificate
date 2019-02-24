from django.db import transaction
from django.conf import settings

from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication
from clublink.certificates.manager import CertificatesManager

from .serializers import CertificateSerializer
from clublink.certificates.models import CertificateBatch, Certificate, CertificateType

from raven.contrib.django.raven_compat.models import client as raven_client

from clublink.base.clients.ibs import WebMemberClient

class CertificateView(APIView):
    """
    Create a new Gift Certificate.
    """
    authentication_classes = (BasicAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        Create a new Gift Certificate.
        """
        serializer = CertificateSerializer(data=request.data, context={'employee': request.user})
        serializer.is_valid(raise_exception=True)

        # Ensure a connection to IBS is possible
        ibs_client = WebMemberClient()
        if not ibs_client.ping() and False:
            return Response(_('Unable to connect to IBS.'), status=http_status.HTTP_400_BAD_REQUEST)

        certificate_manager = CertificatesManager()

        batch = certificate_manager.create_certificate_batch(
            request, 
            serializer.certificate_batch_data,
            serializer.certificate_data
            )

        status, errors = certificate_manager.register_certificate(ibs_client, batch)

        if status:
            try:
                certificate_manager.send_certificate_batch_email(batch, delay=5*60)
            except Exception as e:
                raven_client.captureException()
                return Response(errors, status=http_status.HTTP_400_BAD_REQUEST)
        else:
            batch.delete()
            return Response(errors, status=http_status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=http_status.HTTP_200_OK)
