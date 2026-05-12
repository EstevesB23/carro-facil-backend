from django.test import TestCase
from rest_framework.test import APIClient
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rentals.models import Car, Rental, CustomerRewards, RewardTransaction
from rentals import rewards_service


class CarAPITestCase(TestCase):
    """Tests for Car API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.car = Car.objects.create(
            brand="Toyota", model="Corolla", year=2020,
            daily_rate=Decimal("50.00"), available=True
        )

    def test_deve_listar_carros_disponiveis(self):
        """Should return list of available cars"""
        response = self.client.get('/api/cars/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('cars', response.data)

    def test_deve_obter_carro_por_id(self):
        """Should return a specific car by id"""
        response = self.client.get(f'/api/cars/{self.car.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['brand'], 'Toyota')

    def test_carro_inexistente_retorna_404(self):
        """Should return 404 for non-existent car"""
        response = self.client.get('/api/cars/99999/')
        self.assertEqual(response.status_code, 404)


class RewardsCalculationTestCase(TestCase):
    """Tests for points calculation business rules"""

    def _make_rental(self, daily_rate, days, returned_on_time=True):
        """Helper to create a rental for testing"""
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
        """Economy car (< R$300): base points + on-time bonus only"""
        rental = self._make_rental(daily_rate=200, days=5)
        points = rewards_service.calculate_points(rental)
        # base: 10*5=50, category: 0, duration: 0, on-time: +25 = 75
        self.assertEqual(points, 75)

    def test_pontos_carro_standard(self):
        """Standard car (R$300-499): base points + category bonus"""
        rental = self._make_rental(daily_rate=350, days=5)
        points = rewards_service.calculate_points(rental)
        # base: 50, category: 5*5=25, on-time: +25 = 100
        self.assertEqual(points, 100)

    def test_pontos_carro_premium(self):
        """Premium car (R$500+): base points + category bonus + duration bonus"""
        rental = self._make_rental(daily_rate=600, days=8)
        points = rewards_service.calculate_points(rental)
        # base: 80, category: 10*8=80, duration 7+: +50, on-time: +25 = 235
        self.assertEqual(points, 235)

    def test_sem_bonus_devolucao_atrasada(self):
        """Late return should not receive on-time bonus"""
        rental = self._make_rental(daily_rate=200, days=5, returned_on_time=False)
        points = rewards_service.calculate_points(rental)
        # base: 50, no on-time bonus = 50
        self.assertEqual(points, 50)

    def test_bonus_14_dias(self):
        """14+ day rental should receive the higher duration bonus"""
        rental = self._make_rental(daily_rate=200, days=14)
        points = rewards_service.calculate_points(rental)
        # base: 140, duration 14+: +150, on-time: +25 = 315
        self.assertEqual(points, 315)

    def test_bonus_7_dias(self):
        """7+ day rental should receive duration bonus"""
        rental = self._make_rental(daily_rate=200, days=7)
        points = rewards_service.calculate_points(rental)
        # base: 70, duration 7+: +50, on-time: +25 = 145
        self.assertEqual(points, 145)


class RewardsAPITestCase(TestCase):
    """Tests for rewards API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.car = Car.objects.create(
            brand="Audi", model="Q3", year=2022,
            daily_rate=Decimal("600.00"), available=False
        )
        start = timezone.now() - timedelta(days=8)
        end = timezone.now()
        self.rental = Rental.objects.create(
            car=self.car, customer_name="John Silva",
            customer_email="john@example.com",
            start_date=start, end_date=end,
            actual_return_date=end,
            total_cost=Decimal("4800.00"), returned=True
        )
        rewards_service.award_points_for_rental(self.rental)

    def test_obter_recompensas_cliente(self):
        """Should return customer rewards balance and tier"""
        response = self.client.get('/api/rewards/customer/john@example.com/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_points', response.data)
        self.assertIn('tier', response.data)
        self.assertIn('points_to_next_tier', response.data)
        self.assertIn('lifetime_points_earned', response.data)

    def test_obter_historico_cliente(self):
        """Should return customer points transaction history"""
        response = self.client.get('/api/rewards/customer/john@example.com/history/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('transactions', response.data)
        self.assertEqual(len(response.data['transactions']), 1)
        self.assertEqual(response.data['transactions'][0]['type'], 'earned')

    def test_cliente_inexistente_retorna_404(self):
        """Should return 404 for customer with no rewards"""
        response = self.client.get('/api/rewards/customer/nobody@example.com/')
        self.assertEqual(response.status_code, 404)

    def test_resgatar_pontos(self):
        """Should successfully redeem points for discount"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        rewards.total_points = 500
        rewards.save()

        data = {
            "rental_id": self.rental.id,
            "customer_email": "john@example.com",
            "points_to_redeem": 100
        }
        response = self.client.post('/api/rewards/apply/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('discount_value', response.data)
        self.assertEqual(response.data['discount_value'], 50.0)

        rewards.refresh_from_db()
        self.assertEqual(rewards.total_points, 400)

    def test_resgatar_pontos_insuficientes(self):
        """Should return 400 when customer has insufficient points"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        rewards.total_points = 50
        rewards.save()

        data = {
            "rental_id": self.rental.id,
            "customer_email": "john@example.com",
            "points_to_redeem": 100
        }
        response = self.client.post('/api/rewards/apply/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_nivel_bronze(self):
        """Customer with 0-499 points should be Bronze tier"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        rewards.total_points = 100
        rewards.save()
        self.assertEqual(rewards.tier, "Bronze")
        self.assertEqual(rewards.tier_multiplier, 1.0)
        self.assertEqual(rewards.points_to_next_tier, 400)

    def test_nivel_prata(self):
        """Customer with 500-999 points should be Silver tier"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        rewards.total_points = 500
        rewards.save()
        self.assertEqual(rewards.tier, "Prata")
        self.assertEqual(rewards.tier_multiplier, 1.25)
        self.assertEqual(rewards.points_to_next_tier, 500)

    def test_nivel_ouro(self):
        """Customer with 1000+ points should be Gold tier"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        rewards.total_points = 1000
        rewards.save()
        self.assertEqual(rewards.tier, "Ouro")
        self.assertEqual(rewards.tier_multiplier, 1.5)
        self.assertEqual(rewards.points_to_next_tier, 0)

    def test_pontos_concedidos_automaticamente(self):
        """Points should be automatically awarded when rental is returned"""
        rewards = CustomerRewards.objects.get(customer_email="john@example.com")
        self.assertGreater(rewards.total_points, 0)
        self.assertGreater(rewards.lifetime_points_earned, 0)

        transactions = RewardTransaction.objects.filter(
            customer_rewards=rewards,
            transaction_type='earned'
        )
        self.assertEqual(transactions.count(), 1)

    def test_fluxo_completo_locacao_devolucao_pontos(self):
        """End-to-end: create rental via API -> return via API -> verify points awarded"""
        # Criar um carro disponível
        car = Car.objects.create(
            brand="Mercedes", model="C200", year=2023,
            daily_rate=Decimal("600.00"), available=True
        )

        # Criar locação via API
        create_data = {
            "car_id": car.id,
            "customer_name": "Maria Silva",
            "customer_email": "maria@example.com",
            "days": 8
        }
        create_response = self.client.post('/api/rentals/create', create_data, format='json')
        self.assertEqual(create_response.status_code, 201)

        rental_id = create_response.data['id']

        # Verificar que ainda não tem pontos
        rewards_before = CustomerRewards.objects.filter(customer_email="maria@example.com")
        self.assertFalse(rewards_before.exists())

        # Devolver via API
        return_response = self.client.post(f'/api/rentals/{rental_id}/return/')
        self.assertEqual(return_response.status_code, 200)

        # Verificar que os pontos foram concedidos automaticamente
        rewards = CustomerRewards.objects.get(customer_email="maria@example.com")
        self.assertGreater(rewards.total_points, 0)
        self.assertEqual(rewards.lifetime_points_earned, rewards.total_points)

        # Verificar que existe uma transação do tipo 'earned'
        transaction = RewardTransaction.objects.get(
            customer_rewards=rewards,
            transaction_type='earned'
        )
        self.assertIsNotNone(transaction)
        self.assertGreater(transaction.points, 0)

        # Verificar que os pontos batem com o cálculo esperado
        # base: 10*8=80, premium: 10*8=80, duração 7+: +50, pontual: +25 = 235
        self.assertEqual(rewards.total_points, 235)

        # Verificar que o histórico aparece na API
        history_response = self.client.get('/api/rewards/customer/maria@example.com/history/')
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.data['transactions']), 1)
        self.assertEqual(history_response.data['transactions'][0]['type'], 'earned')