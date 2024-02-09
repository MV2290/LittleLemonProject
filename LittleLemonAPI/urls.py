from django.urls import path, include
from .views import *

urlpatterns = [
    path('menu-items/', MenuItemsView.as_view(), name='menu-items-list'),
    path('menu-items/<int:pk>/', SingleMenuItemView.as_view(), name='menu-item-detail'),
    path('categories/', CategoryView.as_view(), name='category-list'),
    path('groups/<str:group_name>/users',list_group_members),
    path('cart/menu-items/', CartView),
    path('order/', OrderView.as_view()),
    path('order/<int:orderId>/', OrderDetailView.as_view()),

]
