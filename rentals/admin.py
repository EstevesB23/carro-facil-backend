from django.contrib import admin
from .models import Car, Rental, CustomerRewards, RewardTransaction


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['brand', 'model', 'year', 'daily_rate', 'available']
    list_filter = ['available']
    search_fields = ['brand', 'model']


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'customer_email', 'car', 'start_date', 'end_date', 'returned']
    list_filter = ['returned']
    search_fields = ['customer_name', 'customer_email']


@admin.register(CustomerRewards)
class CustomerRewardsAdmin(admin.ModelAdmin):
    list_display = ['customer_email', 'total_points', 'tier', 'lifetime_points_earned', 'lifetime_points_redeemed']
    search_fields = ['customer_email']


@admin.register(RewardTransaction)
class RewardTransactionAdmin(admin.ModelAdmin):
    list_display = ['customer_rewards', 'transaction_type', 'points', 'reason', 'created_at']
    list_filter = ['transaction_type']