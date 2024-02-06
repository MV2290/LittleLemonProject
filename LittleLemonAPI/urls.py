from django.urls import path, include
from .views import *

urlpatterns = [
    path('menu-items/', MenuItemsView.as_view(), name='menu-items-list'),
    path('menu-items/<int:pk>/', SingleMenuItemView.as_view(), name='menu-item-detail'),
    path('categories/', CategoryView.as_view(), name='category-list'),
    path('order-items/', OrderItemView.as_view(), name='order-item-list'),
    path('orders/', OrderView.as_view(), name='order-list'),
    path('groups/<str:group_name>/users',list_group_members),
    path('cart/menu-items/', CartView),
    # Include Djoser URLs
    #path('auth/', include('djoser.urls')),
    #path('auth/', include('djoser.urls.authtoken')),
]
