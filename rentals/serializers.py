from rest_framework import serializers

from .models import Car, Rental, CustomerRewards, RewardTransaction


class CarSerializer(serializers.ModelSerializer):
    """Serializer para modelo Carro"""
    class Meta:
        model = Car
        fields = ['id', 'brand', 'model', 'year', 'daily_rate', 'available', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rental
        fields = [
            'id', 'car', 'customer_name', 'customer_email',
            'start_date', 'end_date', 'total_cost', 'returned',
            'actual_return_date', 'late_fee', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RentalCreateSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    customer_name = serializers.CharField(max_length=200)
    customer_email = serializers.EmailField()
    days = serializers.IntegerField(min_value=1)


class RewardTransactionSerializer(serializers.ModelSerializer):
    """Serializa uma transação de pontos para o histórico"""
    type = serializers.CharField(source='transaction_type')
    timestamp = serializers.DateTimeField(source='created_at')
    rental_id = serializers.SerializerMethodField()

    class Meta:
        model = RewardTransaction
        fields = ['id', 'type', 'points', 'reason', 'rental_id', 'timestamp']

    def get_rental_id(self, obj):
        return obj.rental.id if obj.rental else None


class CustomerRewardsSerializer(serializers.ModelSerializer):
    """Serializa o saldo e nível do cliente"""
    tier = serializers.ReadOnlyField()
    points_to_next_tier = serializers.ReadOnlyField()

    class Meta:
        model = CustomerRewards
        fields = [
            'customer_email', 'total_points', 'tier',
            'points_to_next_tier', 'lifetime_points_earned', 'lifetime_points_redeemed'
        ]


class RedeemPointsSerializer(serializers.Serializer):
    """Valida os dados de entrada para resgate de pontos"""
    rental_id = serializers.IntegerField()
    customer_email = serializers.EmailField()
    points_to_redeem = serializers.IntegerField(min_value=100)