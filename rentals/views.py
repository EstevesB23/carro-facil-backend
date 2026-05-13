import csv
from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import database, rewards_service
from .models import Car, Rental, CustomerRewards, RewardTransaction
from .serializers import (
    CarSerializer,
    RentalSerializer,
    RentalCreateSerializer,
    CustomerRewardsSerializer,
    RewardTransactionSerializer,
    RedeemPointsSerializer,
)


@api_view(['GET'])
def index(request):
    """Endpoint de boas-vindas"""
    return Response({"message": "Welcome to Car Rental API"})


@api_view(['GET'])
def get_cars(request):
    cars = database.get_available_cars()
    serializer = CarSerializer(cars, many=True)
    return Response({"cars": serializer.data})


@api_view(['GET'])
def get_car(request, car_id):
    car = database.get_car_by_id(car_id)
    if car is None:
        return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = CarSerializer(car)
    return Response(serializer.data)


@api_view(['POST'])
def create_rental(request):
    """
    Criar uma nova locação
    """
    serializer = RentalCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    car_id = data['car_id']
    days = data['days']

    # Encontrar carro
    car = database.get_car_by_id(car_id)
    if car is None:
        return Response({"error": "Car not found"}, status=status.HTTP_404_NOT_FOUND)

    if car.available == False:
        return Response({"error": "Car is not available"}, status=status.HTTP_400_BAD_REQUEST)

    # Calcular custo
    total_cost = car.daily_rate * days

    # Aplicar desconto
    if days > 7:
        total_cost = total_cost - (total_cost * Decimal('0.1'))
    elif days > 3:
        total_cost = total_cost - (total_cost * Decimal('0.05'))

    # Criar locação
    start_date = timezone.now()
    end_date = start_date + timedelta(days=days)

    rental = database.create_rental(
        car_id=car_id,
        customer_name=data['customer_name'],
        customer_email=data['customer_email'],
        start_date=start_date,
        end_date=end_date,
        total_cost=Decimal(str(total_cost))
    )

    # Marcar carro como indisponível
    car.available = False
    database.update_car(car)

    rental_serializer = RentalSerializer(rental)
    return Response(rental_serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def return_rental(request, rental_id):
    rental = database.get_rental_by_id(rental_id)

    if rental is None:
        return Response({"error": "Rental not found"}, status=status.HTTP_404_NOT_FOUND)

    if rental.returned == True:
        return Response({"error": "Car already returned"}, status=status.HTTP_400_BAD_REQUEST)

    # Marcar como retornado
    rental.returned = True
    rental.actual_return_date = timezone.now()

    # Calcular multas de atraso
    if rental.actual_return_date > rental.end_date:
        late_days = (rental.actual_return_date - rental.end_date).days
        car = rental.car
        late_fee = float(car.daily_rate) * late_days * 1.5
        rental.late_fee = Decimal(str(late_fee))
        rental.total_cost = rental.total_cost + rental.late_fee

    database.update_rental(rental)

    # Marcar carro como disponível
    car = rental.car
    car.available = True
    database.update_car(car)

    rewards_service.award_points_for_rental(rental)

    serializer = RentalSerializer(rental)
    return Response({
        "message": "Car returned successfully",
        "rental": serializer.data
    })


@api_view(['GET'])
def get_rentals(request):
    rentals = database.get_all_rentals()
    serializer = RentalSerializer(rentals, many=True)
    return Response({"rentals": serializer.data})


@api_view(['GET'])
def get_customer_rentals(request, customer_email):
    """Obter locações para um cliente específico"""
    rentals = database.get_customer_rentals(customer_email)
    serializer = RentalSerializer(rentals, many=True)
    return Response({"rentals": serializer.data})


@api_view(['GET'])
def get_stats(request):
    stats = database.get_rental_stats()
    return Response(stats)


@api_view(['GET'])
def get_customer_rewards(request, customer_email):
    """
    Retorna o saldo de pontos e nível do cliente.
    GET /api/rewards/customer/{customer_email}/
    """
    try:
        rewards = CustomerRewards.objects.get(customer_email=customer_email)
    except CustomerRewards.DoesNotExist:
        return Response(
            {"error": "Cliente não encontrado ou sem pontos ainda."},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = CustomerRewardsSerializer(rewards)
    return Response(serializer.data)


@api_view(['GET'])
def get_rewards_history(request, customer_email):
    """
    Retorna o histórico de transações de pontos do cliente.
    GET /api/rewards/customer/{customer_email}/history/
    Suporta paginação via query params: ?page=1&page_size=10
    """
    try:
        rewards = CustomerRewards.objects.get(customer_email=customer_email)
    except CustomerRewards.DoesNotExist:
        return Response({"error": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    offset = (page - 1) * page_size

    transactions = rewards.transactions.all()
    total = transactions.count()
    transactions_page = transactions[offset:offset + page_size]

    serializer = RewardTransactionSerializer(transactions_page, many=True)
    return Response({
        "customer_email": customer_email,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "transactions": serializer.data
    })


@api_view(['POST'])
def apply_rewards(request):
    """
    Resgata pontos do cliente para desconto em uma locação.
    POST /api/rewards/apply/
    """
    serializer = RedeemPointsSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    rental = database.get_rental_by_id(data['rental_id'])
    if rental is None:
        return Response({"error": "Locação não encontrada."}, status=status.HTTP_404_NOT_FOUND)

    try:
        transaction = rewards_service.redeem_points(
            customer_email=data['customer_email'],
            points_to_redeem=data['points_to_redeem'],
            rental=rental
        )
        return Response({
            "message": f"{data['points_to_redeem']} pontos resgatados com sucesso.",
            "discount_value": (data['points_to_redeem'] / 100) * 50,
            "transaction_id": transaction.id
        })
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def export_rewards_csv(request, customer_email):
    """
    Exporta o histórico de pontos do cliente em CSV.
    GET /api/rewards/customer/{customer_email}/export/
    """
    try:
        rewards = CustomerRewards.objects.get(customer_email=customer_email)
    except CustomerRewards.DoesNotExist:
        return Response({"error": "Cliente não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rewards_{customer_email}.csv"'

    writer = csv.writer(response)

    # Cabeçalho com resumo do cliente
    writer.writerow(['Customer Email', 'Total Points', 'Tier', 'Lifetime Earned', 'Lifetime Redeemed'])
    writer.writerow([
        rewards.customer_email,
        rewards.total_points,
        rewards.tier,
        rewards.lifetime_points_earned,
        rewards.lifetime_points_redeemed,
    ])

    writer.writerow([])  # linha em branco

    # Histórico de transações
    writer.writerow(['Date', 'Type', 'Points', 'Reason', 'Rental ID'])
    for transaction in rewards.transactions.all():
        writer.writerow([
            transaction.created_at.strftime('%Y-%m-%d %H:%M'),
            transaction.transaction_type,
            transaction.points,
            transaction.reason,
            transaction.rental.id if transaction.rental else '',
        ])

    return response