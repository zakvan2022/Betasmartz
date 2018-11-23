import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import serializers
from rest_framework import views
from rest_framework import parsers, views
from ..views import ApiViewMixin
from django.db.models import Q

logger = logging.getLogger('api.v1.validation.views')


class PhoneNumberValidationView(ApiViewMixin, views.APIView):
    serializer_class = serializers.PhoneNumberValidationSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        parsers.JSONParser,
    )

    def post(self, request):
        """
        ---
        # Swagger
        request_serializer: serializers.PhoneNumberValidationSerializer
        response_serializer: serializers.PhoneNumberValidationSerializer

        responseMessages:
            - code: 400
              message: Invalid phone number
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class EmailValidationView(ApiViewMixin, views.APIView):
    serializer_class = serializers.EmailValidationSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        parsers.JSONParser,
    )

    def post(self, request):
        """
        ---
        # Swagger
        request_serializer: serializers.EmailValidationSerializer
        response_serializer: serializers.EmailValidationSerializer

        responseMessages:
            - code: 400
              message: The email is already in use
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class IBAccountValidationView(ApiViewMixin, views.APIView):
    serializer_class = serializers.IBAccountValidationSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        parsers.JSONParser,
    )

    def post(self, request):
        """
        ---
        # Swagger
        request_serializer: serializers.IBAccountValidationSerializer
        response_serializer: serializers.IBAccountValidationSerializer

        responseMessages:
            - code: 400
              message: IB account number is not available | Another client already exists with this IB account number
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class CompositeValidationView(ApiViewMixin, views.APIView):
    serializer_class = serializers.CompositeValidationSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (
        parsers.JSONParser,
    )

    def post(self, request):
        """
        ---
        # Swagger
        request_serializer: serializers.IBAccountValidationSerializer
        response_serializer: serializers.IBAccountValidationSerializer
        requestMessages:
          {
            phone_numbers: [ # optional, array of phone numbers
              ...
            ],
            emails: [ # optional, array of emails
              ...
            ],
            ib_account_numbers: [ # optional, array of account numbers
              ...
            ]
          }
        responseMessages:
            - code: 200
              Response: {
                phone_numbers: [ # if requested
                  {
                    number: '...' # requested number (string)
                    errors: ['...'] # error message, Not set if valid
                  }
                ],
                emails: [ # if requested
                  {
                    email: '...' # requested email
                    errors: ['...'] # error message, Not set if valid
                  }
                ],
                ib_account_numbers: [ # if requested
                  {
                    account_number: '...' # requested ib account number
                    errors: ['...'] # error message, Not set if valid
                  }
                ]
              }
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid()
        return Response(serializer.validated_data)
