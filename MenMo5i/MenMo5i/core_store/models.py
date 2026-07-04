import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


class CartItem(models.Model):
    class Size(models.TextChoices):
        S = 's', 'S'
        M = 'm', 'M'
        L = 'l', 'L'
        XL = 'xl', 'XL'
        XXL = 'xxl', '2XL'

    class Color(models.TextChoices):
        BLACK = 'black', 'Black'
        WHITE = 'white', 'White'
        HEATHER_GREY = 'heather_grey', 'Heather Grey'
        NAVY = 'navy', 'Navy'
        FOREST_GREEN = 'forest_green', 'Forest Green'
        BURGUNDY = 'burgundy', 'Burgundy'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    art = models.ForeignKey('generation_engine.GeneratedArt', on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=8, choices=Size.choices, default=Size.M)
    color = models.CharField(max_length=32, choices=Color.choices, default=Color.BLACK)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'art', 'size', 'color')

    @property
    def total_price(self):
        return self.quantity * self.art.price

    def __str__(self):
        return f"{self.user.username} x{self.quantity} — {self.art}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'

    class PaymentMethod(models.TextChoices):
        COD = 'cod', 'Cash on Delivery'
        CARD = 'card', 'Card Payment'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    shipping_name = models.CharField(max_length=255, blank=True, default='')
    shipping_address = models.TextField(blank=True, default='')
    shipping_city = models.CharField(max_length=128, blank=True, default='')
    shipping_phone = models.CharField(max_length=32, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.COD)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None
        if not is_new:
            try:
                old_status = Order.objects.only('status').get(pk=self.pk).status
            except Order.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if is_new:
            OrderStatusLog.objects.create(order=self, status=self.status, note='Order placed')
            _notify_order_status(self, 'Order placed')
        elif old_status and old_status != self.status:
            OrderStatusLog.objects.create(order=self, status=self.status)
            _notify_order_status(self)

    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.get_status_display()}"


def _notify_order_status(order, note=None):
    """Send email notification about order status change."""
    try:
        subject = f"MenMo5i — Order #{order.pk} is now {order.get_status_display()}"
        message = render_to_string('core_store/email/order_status.txt', {
            'order': order,
            'note': note,
        })
        html_message = render_to_string('core_store/email/order_status.html', {
            'order': order,
            'note': note,
        })
        recipient = order.user.email
        if recipient:
            send_mail(
                subject=subject,
                message=message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=True,
            )
    except Exception as e:
        logger.warning(f"Failed to send order status email: {e}")


class OrderStatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"#{self.order.pk} → {self.get_status_display()} @ {self.created_at:%H:%M}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    art = models.ForeignKey('generation_engine.GeneratedArt', on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    size = models.CharField(max_length=8, choices=CartItem.Size.choices, default=CartItem.Size.M)
    color = models.CharField(max_length=32, choices=CartItem.Color.choices, default=CartItem.Color.BLACK)

    def __str__(self):
        return f"{self.quantity}x {self.art} @ {self.price} TND"
