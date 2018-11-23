from api.v1.serializers import ReadOnlyModelSerializer
from api.v1.user.serializers import UserFieldSerializer
from firm.models import AuthorisedRepresentative


class AuthorisedRepresentativeSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = AuthorisedRepresentative
        exclude = (
            'user',
        )


class AuthorisedRepresentativeFieldSerializer(ReadOnlyModelSerializer):
    user = UserFieldSerializer()

    class Meta:
        model = AuthorisedRepresentative
        fields = (
            'id',
            'gender',
            'work_phone_num',
            'user',
            'firm',
            'email'
        )
