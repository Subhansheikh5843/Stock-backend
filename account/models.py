from django.db import models
from django.contrib.auth.models import BaseUserManager,AbstractBaseUser
from django.conf import settings
from decimal import Decimal, ROUND_DOWN

class UserManager(BaseUserManager):
    def create_user(self, email, name, tc, current_balance=0.00, password=None, password2=None):
        if not email:
            raise ValueError('User must have an email address')

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            tc=tc,
            current_balance=current_balance  # set here
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, tc, password=None):
        user = self.create_user(email, name, tc, current_balance=0.00, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user



class User(AbstractBaseUser):
  email = models.EmailField(
      verbose_name='Email',
      max_length=255,
      unique=True,
  )
  current_balance = models.DecimalField(
        max_digits=10,      
        decimal_places=2,   
        default=0.00        
    )
  name = models.CharField(max_length=200)
  tc = models.BooleanField()
  is_active = models.BooleanField(default=True)
  is_admin = models.BooleanField(default=False)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  objects = UserManager()

  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = ['name', 'tc']

  def __str__(self):
      return self.email

  def has_perm(self, perm, obj=None):
      "Does the user have a specific permission?"
      return self.is_admin

  def has_module_perms(self, app_label):
      "Does the user have permissions to view the app `app_label`?"
      return True

  @property
  def is_staff(self):
      "Is the user a member of staff?"
      return self.is_admin




class Stock(models.Model):
    symbol      = models.CharField(max_length=10, unique=True)
    name        = models.CharField(max_length=100)
    last_price  = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.symbol} ({self.last_price})"
    



class Transaction(models.Model):
    BUY   = 'BUY'
    SELL  = 'SELL'
    TYPE_CHOICES = [
        (BUY, 'Buy'),
        (SELL, 'Sell'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stock       = models.ForeignKey('Stock', on_delete=models.CASCADE)
    tx_type     = models.CharField(max_length=4, choices=TYPE_CHOICES)
    quantity    = models.PositiveIntegerField()
    price_each  = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp   = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = (self.price_each * self.quantity).quantize(
                Decimal('.01'), rounding=ROUND_DOWN
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} {self.tx_type} {self.quantity}×{self.stock.symbol} @ {self.price_each}"
