import json

from rest_framework import generics, response, serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.throttling import UserRateThrottle

from abuse.models import AbuseReport

from mkt.account.api import UserSerializer
from mkt.api.authentication import (RestOAuthAuthentication,
                                    RestAnonymousAuthentication,
                                    RestSharedSecretAuthentication)
from mkt.api.base import CORSMixin
from mkt.webapps.api import AppSerializer



class AbuseThrottle(UserRateThrottle):
    THROTTLE_RATES = {
        'user': '30/hour',
    }


class BaseAbuseSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='message')
    ip_address = serializers.CharField(required=False)
    reporter = UserSerializer()

    def save(self, force_insert=False):
        serializers.ModelSerializer.save(self)
        del self.data['ip_address']
        return self.object


class UserAbuseSerializer(BaseAbuseSerializer):
    user = UserSerializer()
    class Meta:
        model = AbuseReport
        fields = ('text', 'ip_address', 'reporter', 'user')


class AppAbuseSerializer(BaseAbuseSerializer):
    app = AppSerializer(source='addon')
    class Meta:
        model = AbuseReport
        fields = ('text', 'ip_address', 'reporter', 'app')


class BaseAbuseViewSet(CORSMixin, generics.CreateAPIView,
                       viewsets.ModelViewSet):
    cors_allowed_methods = ['post']
    throttle_classes = (AbuseThrottle,)
    throttle_scope = 'user'
    authentication_classes = [RestOAuthAuthentication,
                              RestSharedSecretAuthentication,
                              RestAnonymousAuthentication]
    permission_classes = (AllowAny,)

    def create(self, request, *a, **kw):
        if request.DATA.get('tuber', False):
            return response.Response(json.dumps({'tuber': 'Invalid value'}), 400)
        if request.DATA.get('sprout', None) != 'potato':
            return response.Response(json.dumps({'sprout': 'Invalid value'}), 400)
        if request.amo_user:
            request.DATA['reporter'] = request.amo_user.pk
        else:
            request.DATA['reporter'] = None
        request.DATA['ip_address'] = request.META.get('REMOTE_ADDR', '')
        return viewsets.ModelViewSet.create(self, request, *a, **kw)

    def post_save(self, obj, created=False):
        obj.send()


class AppAbuseViewSet(BaseAbuseViewSet):
    serializer_class = AppAbuseSerializer


class UserAbuseViewSet(BaseAbuseViewSet):
    serializer_class = UserAbuseSerializer
