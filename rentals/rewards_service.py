"""
Serviço de cálculo e gerenciamento de pontos de recompensa.
Separado das views para facilitar testes e reutilização.
"""
from decimal import Decimal
from .models import CustomerRewards, RewardTransaction


def calculate_points(rental) -> int:
    """
    Calcula os pontos ganhos em uma locação.
    Regras:
    - 10 pontos por dia (base)
    - Bônus por categoria: Econômico (< R$300) = 0, Standard (R$300-499) = +5/dia, Premium (R$500+) = +10/dia
    - Bônus por duração: 7+ dias = +50, 14+ dias = +150
    - Bônus por devolução pontual: +25
    """
    days = (rental.end_date - rental.start_date).days or 1
    daily_rate = rental.car.daily_rate

    # Pontos base
    base_points = 10 * days

    # Bônus por categoria
    category_bonus = 0
    if daily_rate >= Decimal('500'):
        category_bonus = 10 * days
    elif daily_rate >= Decimal('300'):
        category_bonus = 5 * days

    # Bônus por duração
    duration_bonus = 0
    if days >= 14:
        duration_bonus = 150
    elif days >= 7:
        duration_bonus = 50

    # Bônus por devolução pontual
    on_time_bonus = 0
    if rental.actual_return_date and rental.actual_return_date <= rental.end_date:
        on_time_bonus = 25

    return base_points + category_bonus + duration_bonus + on_time_bonus


def get_or_create_customer_rewards(customer_email: str, customer_name: str) -> CustomerRewards:
    """Busca ou cria o registro de recompensas de um cliente."""
    rewards, _ = CustomerRewards.objects.get_or_create(
        customer_email=customer_email,
        defaults={'customer_name': customer_name}
    )
    return rewards


def award_points_for_rental(rental) -> RewardTransaction:
    """
    Concede pontos ao cliente após devolução do carro.
    Aplica o multiplicador de nível e registra a transação.
    """
    rewards = get_or_create_customer_rewards(
        rental.customer_email,
        rental.customer_name
    )

    base_points = calculate_points(rental)
    multiplier = rewards.tier_multiplier
    final_points = round(base_points * multiplier)

    days = (rental.end_date - rental.start_date).days or 1
    reason = (
        f"Locação #{rental.id} - {days} dia(s) com {rental.car.brand} {rental.car.model}"
        f" (multiplicador {multiplier}x)"
    )

    rewards.total_points += final_points
    rewards.lifetime_points_earned += final_points
    rewards.save()

    transaction = RewardTransaction.objects.create(
        customer_rewards=rewards,
        transaction_type='earned',
        points=final_points,
        reason=reason,
        rental=rental
    )

    return transaction


def redeem_points(customer_email: str, points_to_redeem: int, rental) -> RewardTransaction:
    """
    Resgata pontos do cliente para desconto em locação.
    100 pontos = R$50 de desconto. Mínimo: 100 pontos.
    """
    if points_to_redeem < 100:
        raise ValueError("Resgate mínimo é de 100 pontos.")
    if points_to_redeem % 100 != 0:
        raise ValueError("Pontos devem ser múltiplos de 100.")

    rewards = CustomerRewards.objects.get(customer_email=customer_email)

    if rewards.total_points < points_to_redeem:
        raise ValueError(f"Pontos insuficientes. Disponível: {rewards.total_points}")

    rewards.total_points -= points_to_redeem
    rewards.lifetime_points_redeemed += points_to_redeem
    rewards.save()

    discount = (points_to_redeem / 100) * 50
    transaction = RewardTransaction.objects.create(
        customer_rewards=rewards,
        transaction_type='redeemed',
        points=-points_to_redeem,
        reason=f"Resgate de {points_to_redeem} pontos = R${discount:.2f} de desconto na locação #{rental.id}",
        rental=rental
    )

    return transaction