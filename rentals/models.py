from django.db import models
from django.core.validators import MinValueValidator, EmailValidator


class Car(models.Model):
    """
    Modelo de Carro representando veículos disponíveis para locação
    """
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField(validators=[MinValueValidator(1900)])
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cars'
        ordering = ['brand', 'model']

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"


class Rental(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='rentals')
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField(validators=[EmailValidator()])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    returned = models.BooleanField(default=False)
    actual_return_date = models.DateTimeField(null=True, blank=True)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rentals'
        ordering = ['-created_at']

    def __str__(self):
        return f"Rental {self.id} - {self.customer_name}"

class CustomerRewards(models.Model):
    """
    Armazena o saldo de pontos de recompensa de cada cliente.
    Vinculado ao email, que é o identificador do cliente no sistema.
    """
    customer_email = models.EmailField(unique=True, validators=[EmailValidator()])
    customer_name = models.CharField(max_length=200)
    total_points = models.IntegerField(default=0)
    lifetime_points_earned = models.IntegerField(default=0)
    lifetime_points_redeemed = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer_rewards'

    def __str__(self):
        return f"{self.customer_email} - {self.total_points} pontos"

    @property
    def tier(self):
        """Calcula o nível do cliente baseado nos pontos acumulados"""
        if self.total_points >= 1000:
            return "Ouro"
        elif self.total_points >= 500:
            return "Prata"
        return "Bronze"

    @property
    def tier_multiplier(self):
        multipliers = {"Bronze": 1.0, "Prata": 1.25, "Ouro": 1.5}
        return multipliers[self.tier]

    @property
    def points_to_next_tier(self):
        if self.total_points >= 1000:
            return 0
        elif self.total_points >= 500:
            return 1000 - self.total_points
        return 500 - self.total_points


class RewardTransaction(models.Model):
    """
    Histórico de cada transação de pontos (ganho ou resgate).
    Permite auditoria completa dos pontos.
    """
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed'),
    ]

    customer_rewards = models.ForeignKey(
        CustomerRewards,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    points = models.IntegerField()
    reason = models.CharField(max_length=500)
    rental = models.ForeignKey(
        Rental,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reward_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reward_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_rewards.customer_email} - {self.points} pts"
