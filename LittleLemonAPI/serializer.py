from rest_framework import serializers
from .models import *
from rest_framework.validators import UniqueValidator
from django.contrib.auth.models import User
from djoser.serializers import UserCreateSerializer
from django.contrib.auth import get_user_model

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = get_user_model()  # Get the User model dynamically
        fields = ('id', 'email', 'username', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        # Customize the creation logic if needed
        user = get_user_model().objects.create_user(**validated_data)
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','title']

class MenuItemSerializer(serializers.ModelSerializer):
    category_id = serializers.IntegerField(write_only=True)
    category = CategorySerializer(read_only=True)

    def validate(self, attrs):
        # Ensure price is greater than or equal to 2.0
        if attrs['price'] < 2.0:
            raise serializers.ValidationError('Price should not be less than 2.0')
        # Ensure inventory is non-negative
        if attrs['inventory'] < 0:
            raise serializers.ValidationError('Stock cannot be negative')
        return attrs

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'inventory', 'category', 'category_id']
        extra_kwargs = {
            'title': {'validators': [UniqueValidator(queryset=MenuItem.objects.all())]}
        }
        
class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ['id', 'user', 'item', 'quantity', 'unit_price', 'price']

class OrderItemSerializer(serializers.ModelSerializer):
    menuitem_id = serializers.PrimaryKeyRelatedField(source='menuitem', queryset=MenuItem.objects.all())

    class Meta:
        model = OrderItem
        fields = ['order', 'menuitem_id', 'quantity', 'unit_price', 'price']


class DeliveryOrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'delivery_crew_user', 'status', 'total', 'date', 'order_items', 'user']