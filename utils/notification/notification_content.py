from dataclasses import dataclass
from enum import Enum

@dataclass
class NotificationContent:
    title: str
    message: str

class NotificationType(Enum):
    ORDER_PLACED = NotificationContent(
        title="Order Placed",
        message=("New order placed successfully:\n{order_details}")
    )
    ORDER_FAILED = NotificationContent(
        title="Order Failed",
        message=("Failed to place order:\n{error_details}")
    )
    ERROR_OCCURRED = NotificationContent(
        title="Error Occurred",
        message="An error occurred in the trading bot:\n{error_details}."
    )
    TAKE_PROFIT_TRIGGERED = NotificationContent(
        title="Take Profit Triggered",
        message="Take profit triggered with order details:\n{order_details}"
    )
    STOP_LOSS_TRIGGERED = NotificationContent(
        title="Stop Loss Triggered",
        message="Stop loss triggered with order details:\n{order_details}"
    )