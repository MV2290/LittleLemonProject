from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth.models import User, Group
from functools import wraps
from decimal import Decimal

# Create your views here.
class MenuItemsView(generics.ListAPIView, generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price']
    search_fields = ['title']
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            if self.request.user.groups.filter(name='Manager').exists():
                return [IsAuthenticated()]
            else:
                raise PermissionDenied("Request denied, only Manager users allowed") 
        else:
            raise PermissionDenied("Request denied, if you want to update or delete you have to select single item")

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.user.groups.filter(name='Manager').exists():
            return [IsAuthenticated()]
        else:
            raise PermissionDenied("Request denied, only Manager users allowed")

def group_required(group_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)
            else:
                return Response("Permission denied. User must be in the 'Manager' group.", status=status.HTTP_403_FORBIDDEN)

        return wrapper
    return decorator

@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@group_required('Manager')
def list_group_members(request, group_name):
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return Response(f"Group '{group_name}' not found", status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # Get members and return serialized data
        members = group.user_set.all()
        serialized_members = [{'username': member.username, 'email': member.email} for member in members]
        return Response(serialized_members)

    elif request.method == 'POST':
        # Add a new member to the group by username
        username = request.data.get('username', None)
        if username:
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                group.user_set.add(user)
                return Response(f"User '{user.username}' added to group '{group_name}'", status=status.HTTP_201_CREATED)
            except User.DoesNotExist:
                return Response(f"User with username '{username}' not found", status=status.HTTP_404_NOT_FOUND)
        else:
            return Response("Username not provided in the request data", status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # Remove a member from the group
        username = request.data.get('username', None)
        if username:
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
                group.user_set.remove(user)
                return Response(f"User '{user.username}' removed from group '{group_name}'", status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response(f"User with username '{username}' not found", status=status.HTTP_404_NOT_FOUND)
        else:
            return Response("Username not provided in the request data", status=status.HTTP_400_BAD_REQUEST)

    else:
        return Response("Invalid HTTP method", status=status.HTTP_400_BAD_REQUEST)

class CategoryView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    def get_permissions(self):
        print(f"User: {self.request.user}")
    
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        elif self.request.user.groups.filter(name='Manager').exists():
            print("User is in 'Manager' group.")
            return [IsAuthenticated()]
        else:
            print("Permission denied.")
            raise PermissionDenied("Request denied, only Manager users allowed")
        
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def CartView(request):
    user = request.user
    
    if request.method == 'GET':
        carts = Cart.objects.filter(user=user)
        serializer = CartSerializer(carts, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        item_title = request.data.get('item')
        quantity = request.data.get('quantity', 1)  # Default to 1 if quantity is not provided
        
        # Validate and save to the cart using the serializer
        try:
            # Get the selected item by title
            item = MenuItem.objects.get(title=item_title)
            unit_price = item.price
        except MenuItem.DoesNotExist:
            return Response({'message': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)
        
        data = {
            'user':user.id, 'item': item.pk, 'quantity': quantity, 'unit_price': unit_price, 'price': unit_price*Decimal(quantity),
        }
        serializer = CartSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        Cart.objects.filter(user=user).delete()
        return Response({'message': 'Cart emptied successfully'}, status=status.HTTP_204_NO_CONTENT)

    return Response({'message': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)


class OrderView(APIView):

    @permission_classes([IsAuthenticated])
    def get(self, request, *args, **kwargs):
        if request.user.groups.filter(name='Manager').exists():
            orders = OrderItem.objects.all()
        else:
            # Get all orders for the current user
            user = request.user
            orders = OrderItem.objects.filter(order=user)
        
        # Serialize orders
        serializer = OrderItemSerializer(orders, many=True)
        
        return Response(serializer.data)
    
    @permission_classes([IsAuthenticated])
    def post(self, request, *args, **kwargs):
        # Get the current user
        user = request.user
        
        # Retrieve current cart items from the cart endpoints
        cart_items = Cart.objects.filter(user=user)
        
        # Create order items for each cart item
        order_items = []
        for cart_item in cart_items:
            order_item_data = {
                'order': user.id,
                'menuitem_id': cart_item.item.id,
                'quantity': cart_item.quantity,
                'unit_price': cart_item.unit_price,
                'price': cart_item.price
            }
            order_item_serializer = OrderItemSerializer(data=order_item_data)
            if order_item_serializer.is_valid():
                order_item = order_item_serializer.save()
                order_items.append(order_item)
            else:
                return Response(order_item_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Delete all items from the cart for this user
        cart_items.delete()
        return Response("Order created successfully. Cart is now empty.", status=status.HTTP_201_CREATED)
    
    def delete(self, request, *args, **kwargs):
        
        order_number = request.data.get('order')
        
        if self.request.user.groups.filter(name='Manager').exists():
            # Get all order items associated with the orders of the order
            order_items_to_delete = OrderItem.objects.filter(order=order_number)
            # Delete all found order items
            order_items_to_delete.delete()
            return Response({'message': 'All order items deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        else:
            raise PermissionDenied("Request denied, only Manager users allowed")