from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('cars/', views.get_cars, name='get_cars'),
    path('cars/<int:car_id>/', views.get_car, name='get_car'),
    path('rentals/', views.get_rentals, name='get_rentals'),
    path('rentals/create', views.create_rental, name='create_rental'),
    path('rentals/<int:rental_id>/return/', views.return_rental, name='return_rental'),
    path('rentals/customer/<str:customer_email>/', views.get_customer_rentals, name='get_customer_rentals'),
    path('stats/', views.get_stats, name='get_stats'),
    path('rewards/customer/<str:customer_email>/', views.get_customer_rewards, name='get_customer_rewards'),
    path('rewards/customer/<str:customer_email>/history/', views.get_rewards_history, name='get_rewards_history'),
    path('rewards/customer/<str:customer_email>/export/', views.export_rewards_csv, name='export_rewards_csv'),
    path('rewards/apply/', views.apply_rewards, name='apply_rewards'),
]