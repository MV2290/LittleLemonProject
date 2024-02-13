from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from .models import *
from .serializer import *
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.exceptions import PermissionDenied, NotFound
from django.contrib.auth.models import User, Group
from functools import wraps
from decimal import Decimal
from datetime import datetime, timedelta


# Create your views here.
class MenuItemsView(generics.ListAPIView, generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price']
    filter_backends = [OrderingFilter, SearchFilter]
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

@api_view(['GET', 'POST'])
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

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@group_required('Manager')
def remove_user_from_group(request, group_name, user_id):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        group = Group.objects.get(name=group_name)
        if user in group.user_set.all():
            group.user_set.remove(user)
            return Response(f"User '{user.username}' removed from group '{group_name}'", status=status.HTTP_200_OK)
        else:
            return Response(f"User '{user.username}' is not a member of group '{group_name}'", status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response(f"User with ID '{user_id}' not found", status=status.HTTP_404_NOT_FOUND)
    except Group.DoesNotExist:
        return Response(f"Group with name '{group_name}' not found", status=status.HTTP_404_NOT_FOUND)

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
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
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
    ordering_fields = ['order']
    filter_backends = [OrderingFilter, SearchFilter]
    search_fields = ['order']
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    @permission_classes([IsAuthenticated])
    def get(self, request):
        user = request.user
        if user.groups.filter(name='Manager').exists():
            orders = OrderItem.objects.all()
        elif user.groups.filter(name='delivery-crew').exists():
            # Filter OrderItem instances based on the order and delivery crew
            delivery_crew = user.pk
            orders = OrderItem.objects.filter(order__delivery_crew=delivery_crew)
        else:
            try:
                orders = OrderItem.objects.filter(order=user)
            except:
                return Response({"No user provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Serialize orders
        serializer = OrderItemSerializer(orders, many=True)
        
        return Response(serializer.data)
    
    @permission_classes([IsAuthenticated])
    def post(self, request):
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

class OrderDetailView(APIView):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]
    @permission_classes([IsAuthenticated])
    def get(self, reqeust, orderId):
        try:
            order_item = OrderItem.objects.get(id=orderId)
        except OrderItem.DoesNotExist:
            return Response({"message": "OrderItem not found"}, status=status.HTTP_404_NOT_FOUND)
             
        serializer = OrderItemSerializer(order_item)
        return Response(serializer.data)
    
    def delete(self, orderId):
        try:
            order = OrderItem.objects.get(id=orderId)
        except OrderItem.DoesNotExist:
            raise NotFound("Order not found")
        
        if self.request.user.groups.filter(name='Manager').exists():
            order.delete()
            return Response({'message': 'All order items deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)
        else:
            raise PermissionDenied("Request denied, only Manager users allowed")
        
    def post(self, request, orderId):
        # Check if the user is a manager
        if not request.user.groups.filter(name='Manager').exists():
            raise PermissionDenied("Only managers can create orders")

        # Logic to assign a delivery crew user (you may need to customize this logic)
        delivery_crew_user = User.objects.filter(groups__name='delivery-crew').first()
        if delivery_crew_user is None:
            return Response({"message": "No delivery crew available"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Retrieve order items as a queryset
        order_items_queryset = OrderItem.objects.filter(id=orderId)

        # Calculate the total price of the order based on the prices of the order items
        total_price = sum(order_item.price for order_item in order_items_queryset)
        
        # Retrieve the user associated with the order
        user = order_items_queryset.first().order  # Assuming all order items belong to the same user

        # Calculate delivery date (today plus one week)
        delivery_date = datetime.now() + timedelta(weeks=1)

        # Extract only the date part from the delivery_date
        delivery_date_date = delivery_date.date()

        # Prepare the data for creating the order
        order_data = {
            'user': user.id,
            'delivery_crew_user': delivery_crew_user.id,
            'status': request.data.get('status'),
            'total': total_price,
            'date': delivery_date_date,
        }

        # Serialize the order data
        serializer = DeliveryOrderSerializer(data=order_data)
        if serializer.is_valid():
            order_instance = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, orderId):
        # Retrieve the order item
        try:
            order_item = OrderItem.objects.get(id=orderId)
        except OrderItem.DoesNotExist:
            return Response({"message": "OrderItem not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the user is part of the delivery crew
        if request.user.groups.filter(name='delivery-crew').exists():
            # Extract the status from the request data
            status_value = int(request.data.get('status'))
            if status_value in [0, 1]:  # Ensure status is either 0 or 1
                order_item.status = status_value
                order_item.save()
                serializer = OrderItemSerializer(order_item)
                return Response(serializer.data)
            else:
                return Response({"message": "Invalid status value. Status must be either 0 or 1."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "Only delivery crew users are allowed to update order status."}, status=status.HTTP_403_FORBIDDEN)
 
