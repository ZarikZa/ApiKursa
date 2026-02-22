from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # заставляем SimpleJWT принимать email вместо username
    username_field = "email"

    def validate(self, attrs):
        # превращаем {"email": "...", "password": "..."} в формат, который ждёт базовый сериализатор
        if "email" in attrs and "username" not in attrs:
            attrs["username"] = attrs["email"]

        data = super().validate(attrs)

        data.update({
            'user_id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'user_type': self.user.user_type,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'is_superuser': bool(self.user.is_superuser),
        })
        return data

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)