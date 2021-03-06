import json

from django.core.serializers import get_serializer
from django.http import HttpResponse
from rest_framework import viewsets, status, generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.admin import User
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from backend.models import Photo, Comment, Like, Observation
from backend.serializers import RegisteredUserSerializer, PhotoSerializer, CommentSerializer, SinglePhotoSerializer, \
    LikeSerializer, ObservationSerializer, UserSerializer
from django.db.models import Q

from rest_framework import filters


class PhotoSetPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined').exclude(username=self.request.user)

    serializer_class = RegisteredUserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username']


class RegistrationViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class PhotoViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer

    def get_queryset(self):
        owner_queryset = self.queryset.filter(owner=self.request.user)
        return owner_queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def post(self, request, *args, **kwargs):
        file = request.data['file']
        Photo.objects.create(image=file, owner=request.auth.user)

        return HttpResponse(json.dumps({'message': "Uploaded"}), status=200)


class AllPhotosViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer
    pagination_class = PhotoSetPagination

    def list(self, request, *args, **kwargs):
        following = Observation.objects.values('following').filter(follower=request.auth.user)
        queryset = Photo.objects.filter(Q(owner__in=following) | Q(owner=request.auth.user)).order_by('-created')
        paged = self.paginate_queryset(queryset)
        serializer = PhotoSerializer(paged, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class CurrentUserViewSet(viewsets.ModelViewSet):
    model = User
    serializer_class = RegisteredUserSerializer

    def dispatch(self, request, *args, **kwargs):
        if kwargs.get('pk') == 'current' and request.user:
            kwargs['pk'] = request.user.pk

        return super(CurrentUserViewSet, self).dispatch(request, *args, **kwargs)


class MyProfilePhotosViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Photo.objects.all()
    serializer_class = PhotoSerializer

    def get_queryset(self):
        owner_queryset = self.queryset.filter(owner=self.request.user)
        return owner_queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = PhotoSerializer(queryset, many=True, context={'request': request})
        return Response({'photos': serializer.data, 'username': request.user.username,
                         'followersAmount': Observation.objects.filter(following=request.user).count()})


class CommentViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        comment = Comment.objects.all()
        return comment


class PhotoDetailsViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    queryset = Photo.objects.all()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = SinglePhotoSerializer(instance, context={'request': request})
        return Response(serializer.data)


class LikeViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    serializer_class = LikeSerializer

    def perform_create(self, serializer):
        photo_id = self.kwargs['photo_id']
        if self.kwargs['function'] == 'like':
            serializer.save(owner=self.request.user, photo_id=photo_id)
        else:
            Like.objects.filter(photo_id=photo_id, owner=self.request.user).delete()

    def get_queryset(self):
        photo_id = self.kwargs['photo_id']
        likes = Like.objects.filter(photo_id=photo_id)

        return likes


class ObservationViewSet(viewsets.ModelViewSet):
    authentication_classes = (TokenAuthentication,)
    serializer_class = ObservationSerializer

    def perform_create(self, serializer):
        profile_id = self.kwargs['profile_id']
        if self.kwargs['function'] == 'follow':
            serializer.save(follower=self.request.user, following_id=profile_id)
        else:
            Observation.objects.filter(following_id=profile_id, follower=self.request.user).delete()

    def get_queryset(self):
        profile_id = self.kwargs['profile_id']
        observations = Observation.objects.filter(following_id=profile_id)

        return observations
