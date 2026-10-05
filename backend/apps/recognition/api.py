from rest_framework import mixins, serializers, viewsets

from apps.common.responses import ok
from apps.notifications.services import notify

from .models import Recognition


class RecognitionSerializer(serializers.ModelSerializer):
    giver_name = serializers.CharField(source="giver.full_name", read_only=True)
    receiver_name = serializers.CharField(source="receiver.full_name", read_only=True)
    badge_label = serializers.CharField(source="get_badge_display", read_only=True)

    class Meta:
        model = Recognition
        fields = ["id", "giver_name", "receiver", "receiver_name", "category", "badge", "badge_label", "message", "created_at"]


class RecognitionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = RecognitionSerializer
    queryset = Recognition.objects.select_related("giver", "receiver")
    filterset_fields = ["receiver", "category", "badge"]

    def create(self, request, *a, **kw):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        me = request.user.employee
        if s.validated_data["receiver"].pk == me.pk:
            raise serializers.ValidationError({"receiver": "You cannot recognise yourself."})
        r = s.save(giver=me)
        notify(r.receiver.user, "You were recognised!", f"{me.full_name}: {r.message}", "RECOGNITION", "/recognition/")
        return ok(self.get_serializer(r).data, "Recognition sent", 201)

    def destroy(self, request, *a, **kw):
        from rest_framework.exceptions import PermissionDenied
        r = self.get_object()
        from apps.common.roles import HR_ROLES
        if r.giver.user_id != request.user.pk and request.user.role not in HR_ROLES:
            raise PermissionDenied()
        r.delete()
        return ok({}, "Recognition removed")
