from rest_framework import serializers
from account.models import User
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from .models import (
    User,
    Stock,
    Transaction,
)
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from decimal import Decimal, ROUND_DOWN
from django.db.models import Sum
from rest_framework import serializers


class UserRegistrationSerializer(serializers.ModelSerializer):
  confirm_password = serializers.CharField(style={'input_type':'password'}, write_only=True)
  class Meta:
    model = User
    fields=['email', 'name', 'password', 'confirm_password', 'current_balance']
    extra_kwargs={
      'password':{'write_only':True}
    }

  def validate(self, attrs):
    password = attrs.get('password')
    confirm_password = attrs.get('confirm_password')
    if password != confirm_password:
      raise serializers.ValidationError("Password and Confirm Password doesn't match")
    return attrs
  
  def validate_current_balance(self, value):
        """
        Ensure the user’s starting balance is not negative.
        DRF will call this automatically for the 'current_balance' field.
        """
        if value < 0:
            raise serializers.ValidationError("Balance cannot be negative.")
        return value

  def create(self, validate_data):
    return User.objects.create_user(**validate_data)


class UserLoginSerializer(serializers.ModelSerializer):
  email = serializers.EmailField(max_length=255)

  class Meta:
    model = User
    fields = ['email', 'password']


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Stock
        fields = ['symbol', 'name', 'last_price']


class TransactionSerializer(serializers.ModelSerializer):
    stock = serializers.SlugRelatedField(
        queryset=Stock.objects.all(),
        slug_field='symbol'
    )
    user_balance = serializers.SerializerMethodField()
    price_each = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'stock', 'transaction_type',
            'quantity', 'price_each', 'total_price', 'timestamp',
            'user_balance'
        ]
        read_only_fields = ['total_price', 'timestamp', 'user_balance']

    def get_user_balance(self, obj):
        return float(obj.user.current_balance) 
    
    def get_fields(self):
        """
        Dynamically drop `user_balance` on GET requests.
        """
        fields = super().get_fields()
        request = self.context.get('request', None)
        if request and request.method == 'GET':
            fields.pop('user_balance', None)
        return fields

    def validate(self, attrs):
        user = self.context['request'].user
        stock = attrs['stock']
        quantity = attrs['quantity']
        price = attrs['price_each']
        transaction_type = attrs['transaction_type']
        total_cost = price * quantity

        if transaction_type == Transaction.BUY:
            if user.current_balance < total_cost:
                raise serializers.ValidationError("Insufficient balance for this purchase.")
        elif transaction_type == Transaction.SELL:
           
            total_bought = Transaction.objects.filter(
                user=user,
                stock=stock,
                transaction_type=Transaction.BUY
            ).aggregate(total=Sum('quantity'))['total'] or 0

      
            total_sold = Transaction.objects.filter(
                user=user,
                stock=stock,
                transaction_type=Transaction.SELL
            ).aggregate(total=Sum('quantity'))['total'] or 0


            available_quantity = total_bought - total_sold

            if quantity > available_quantity:
                raise serializers.ValidationError(
                    f"You can only sell up to {available_quantity} shares of {stock.symbol}."
                )

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user

        total_price = (validated_data['price_each'] * validated_data['quantity']).quantize(
            Decimal('.01'), rounding=ROUND_DOWN
        )
        validated_data['total_price'] = total_price

        transaction_created = Transaction.objects.create(user=user, **validated_data)

        if transaction_created.transaction_type == Transaction.BUY:
            user.current_balance -= transaction_created.total_price
        else:
            user.current_balance += transaction_created.total_price
        user.save(update_fields=['current_balance'])

        return transaction_created


class TransactionListSerializer(serializers.ModelSerializer):
    stock = serializers.CharField(source='stock.symbol')

    class Meta:
        model = Transaction
        fields = ['stock', 'transaction_type', 'quantity', 'price_each', 'total_price', 'timestamp']
