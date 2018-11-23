from api.v1.serializers import ReadOnlyModelSerializer
from api.v1.user.serializers import UserFieldSerializer
from firm.models import Supervisor


class SupervisorSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Supervisor
        exclude = (
            'user',
        )


class SupervisorFieldSerializer(ReadOnlyModelSerializer):
    user = UserFieldSerializer()

    class Meta:
        model = Supervisor
        fields = (
            'id',
            'user',
            'firm',
            'email'
        )
