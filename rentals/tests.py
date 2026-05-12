from django.test import TestCase
from rest_framework.test import APIClient
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rentals.models import Car, Rental, CustomerRewards, RewardTransaction
from rentals import rewards_service


class CarAPITestCase(TestCase):
    """Testes para API de Carros"""

    def setUp(self):
        self.client = APIClient()
        self.car = Car.objects.create(
            brand="Toyota", model="Corolla", year=2020,
            daily_rate=Decimal("50.00"), available=True
        )

    def test_deve_listar_carros_disponiveis(self):
        response = self.client.get('/api/cars/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cars', response.data)

    def test_deve_obter_carro_por_id(self):
        response = self.client.get(f'/api/cars/{self.car.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['brand'], 'Toyota')

    def test_carro_inexistente_retorna_404(self):
        response = self.client.get('/api/cars/99999/')
        self.assertEqual(response.status_code, 404)


class RewardsCalculationTestCase(TestCase):
    """Testes para as regras de cálculo de pontos"""

    def _make_rental(self, daily_rate, days, returned_on_time=True):
        car = Car.objects.create(
            brand="Test", model="Car", year=2023,
            daily_rate=Decimal(str(daily_rate)), available=False
        )
        start = timezone.now() - timedelta(days=days)
        end = timezone.now()
        actual_return = end if returned_on_time else end + timedelta(days=2)
        return Rental.objects.create(
            car=car, customer_name="Test User",
            customer_email="test@test.com",
            start_date=start, end_date=end,
            actual_return_date=actual_return,
            total_cost=Decimal(str(daily_rate * days)),
            returned=True
        )

    def test_pontos_carro_economico(self):
        """Carro < R$300: só pontos base + bônus pontual"""
        rental = self._make_rental(daily_rate=200, days=5)
        points = rewards_service.calculate_points(rental)
        # base: 10*5=50, categoria: 0, duração: 0, pontual: +25 = 75
        self.assertEqual(points, 75)

    def test_pontos_carro_standard(self):
        """Carro R$300-499: pontos base + bônus categoria"""
        rental = self._make_rental(daily_rate=350, days=5)
        points = rewards_service.calculate_points(rental)
        # base: 50, categoria: 5*5=25, pontual: +25 = 100
        self.assertEqual(points, 100)

    def test_pontos_carro_premium(self):
        """Carro R$500+: pontos base + bônus categoria + bônus duração"""
        rental = self._make_rental(daily_rate=600, days=8)
        points = rewards_service.calculate_points(rental)
        # base: 80, categoria: 10*8=80, duração 7+: +50, pontual: +25 = 235
        self.assertEqual(points, 235)

    def test_sem_bonus_devolucao_atrasada(self):
        """Devolução atrasada não ganha bônus pontual"""
        rental = self._make_rental(daily_rate=200, days=5, returned_on_time=False)
        points = rewards_service.calculate_points(rental)
        # base: 50, sem pontual = 50
        self.assertEqual(points, 50)

    def test_bonus_14_dias(self):
        """Locação de 14+ dias ganha bônus maior"""
        rental = self._make_rental(daily_rate=200, days=14)
        points = rewards_service.calculate_points(rental)
        # base: 140, duração 14+: +150, pontual: +25 = 315
        self.assertEqual(points, 315)

    def test_bonus_7_dias(self):
        """Locação de 7+ dias ganha bônus de duração"""
        rental = self._make_rental(daily_rate=200, days=7)
        points = rewards_service.calculate_points(rental)
        # base: 70, duração 7+: +50, pontual: +25 = 145
        self.assertEqual(points, 145)


class RewardsAPITestCase(TestCase):
    """Testes para os endpoints de recompensas"""

    def setUp(self):
        self.client = APIClient()
        self.car = Car.objects.create(
            brand="Audi", model="Q3", year=2022,
            daily_rate=Decimal("600.00"), available=False
        )
        start = timezone.now() - timedelta(days=8)
        end = timezone.now()
        self.rental = Rental.objects.create(
            car=self.car, customer_name="João Silva",
            customer_email="joao@example.com",
            start_date=start, end_date=end,
            actual_return_date=end,
            total_cost=Decimal("4800.00"), returned=True
        )
        rewards_service.award_points_for_rental(self.rental)

    def test_obter_recompensas_cliente(self):
        response = self.client.get('/api/rewards/customer/joao@example.com/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_points', response.data)
        self.assertIn('tier', response.data)
        self.assertIn('points_to_next_tier', response.data)

    def test_obter_historico_cliente(self):
        response = self.client.get('/api/rewards/customer/joao@example.com/history/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('transactions', response.data)
        self.assertEqual(len(response.data['transactions']), 1)