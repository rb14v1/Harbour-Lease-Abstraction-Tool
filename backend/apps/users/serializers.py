from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "date_joined"]
        read_only_fields = ["id", "role", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "role"]
        extra_kwargs = {"role": {"required": False}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.setdefault("role", User.ROLE_PROPERTY_MANAGER)
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
