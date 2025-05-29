import logging
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from account.renderers import UserRenderer
from rest_framework import generics, permissions
from django.utils.translation import gettext_lazy as _
from .constants import HARDCODED_STOCKS
from rest_framework import status
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework import generics, permissions
from datetime import datetime
from django.utils.dateparse import parse_date
from .utils import get_tokens_for_user,IsAdminUserCustom
from rest_framework.permissions import IsAuthenticated
from .models import (
    Stock,
    Transaction,
)
from django.db import DatabaseError
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    StockSerializer,
    TransactionSerializer,
    TransactionListSerializer
)


logger = logging.getLogger(__name__)


class UserRegistrationView(APIView):
    """
    POST /api/register/

    Handles user registration by validating the submitted data and creating a new user.
    Upon successful registration, JWT tokens are generated and returned.

    Request body:
    - email
    - password
    - confirm_password

    Response:
    - token (JWT access and refresh)
    - success message
    """
    renderer_classes = [UserRenderer]

    def post(self, request, format=None):
        try:
            serializer = UserRegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            token = get_tokens_for_user(user)
            return Response(
                {'token': token, 'msg': 'Registration Successful'},
                status=status.HTTP_201_CREATED
            )

        except ValidationError as e:
            return Response(
                {'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception("Unexpected error during user registration")
            return Response(
                {'error': _('Something went wrong. Please try again later.')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserLoginView(APIView):
    """
    POST /api/login/

    Authenticates a user based on provided email and password.
    If successful, returns JWT access and refresh tokens.

    Request body:
    - email
    - password

    Response:
    - token (JWT access and refresh)
    - success message

    Error:
    - 400 Bad Request for validation issues
    - 401 Unauthorized if credentials are invalid
    - 500 Internal Server Error for unexpected issues
    """
    renderer_classes = [UserRenderer]

    def post(self, request, format=None):
        try:
            serializer = UserLoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            email = serializer.validated_data.get('email')
            password = serializer.validated_data.get('password')

            user = authenticate(email=email, password=password)

            if user is None:
                raise AuthenticationFailed('Invalid email or password.')

            token = get_tokens_for_user(user)

            return Response(
                {'token': token, 'msg': 'Login Success'},
                status=status.HTTP_200_OK
            )

        except ValidationError as e:
            return Response(
                {'errors': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

        except AuthenticationFailed as e:
            return Response(
                {'errors': {'non_field_errors': [str(e)]}},
                status=status.HTTP_401_UNAUTHORIZED
            )

        except Exception as e:
            logger.exception("Unexpected error during login.")
            return Response(
                {'error': 'An unexpected error occurred. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IngestStocksView(APIView):
    """
    GET → loads the HARDCODED_STOCKS into the DB (creates or updates),
    then returns the full list from the table.

    Only admin users can access this endpoint.
    """
    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated, IsAdminUserCustom]  # <-- enforce admin-only access

    def get(self, request, format=None):
        try:
            created = []

            for data in HARDCODED_STOCKS:
                obj, _ = Stock.objects.update_or_create(
                    symbol=data['symbol'],
                    defaults={
                        'name': data['name'],
                        'last_price': data['last_price']
                    }
                )
                created.append(obj)

            all_stocks = Stock.objects.all()
            serializer = StockSerializer(all_stocks, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except DatabaseError as e:
            logger.error("Database error while loading stocks: %s", str(e))
            return Response(
                {'error': 'A database error occurred while loading stocks.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            logger.exception("Unexpected error while loading stocks.")
            return Response(
                {'error': 'An unexpected error occurred. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    
class StockQueryView(APIView):
    """
    GET  /api/stocks/?symbol=&min_price=&max_price=&ordering=
    
    Query params:
      - symbol:     exact match on ticker (e.g. AAPL)
      - min_price:  last_price >= this value
      - max_price:  last_price <= this value
      - ordering:   field name to order by, prefix with '-' for DESC (e.g. ordering=-last_price)
    """
    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            stocks = Stock.objects.all()

            # Filter by symbol
            symbol = request.query_params.get('symbol')
            if symbol:
                stocks = stocks.filter(symbol__iexact=symbol)

            # Filter by minimum price
            min_price = request.query_params.get('min_price')
            if min_price is not None:
                try:
                    min_price = float(min_price)
                    stocks = stocks.filter(last_price__gte=min_price)
                except ValueError:
                    return Response(
                        {"detail": "min_price must be a numeric value."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Filter by maximum price
            max_price = request.query_params.get('max_price')
            if max_price is not None:
                try:
                    max_price = float(max_price)
                    stocks = stocks.filter(last_price__lte=max_price)
                except ValueError:
                    return Response(
                        {"detail": "max_price must be a numeric value."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Ordering
            ordering = request.query_params.get('ordering')
            allowed_ordering_fields = {
                'last_price', '-last_price',
                'symbol', '-symbol',
                'updated_at', '-updated_at'
            }
            if ordering:
                if ordering in allowed_ordering_fields:
                    stocks = stocks.order_by(ordering)
                else:
                    return Response(
                        {"detail": f"Invalid ordering field: {ordering}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            serializer = StockSerializer(stocks, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except DatabaseError as db_err:
            logger.error("Database error while querying stocks: %s", str(db_err))
            return Response(
                {"error": "A database error occurred while retrieving stock data."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            logger.exception("Unexpected error in StockQueryView")
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TransactionView(generics.ListCreateAPIView):
    """
    GET  /api/transactions/           → list user's transactions
    POST /api/transactions/           → create (buy/sell) a transaction
    """
    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        try:
            # only return this user's transactions, ordered by timestamp desc
            return Transaction.objects.filter(user=self.request.user).order_by('-timestamp')
        except DatabaseError as db_err:
            logger.error(f"Database error fetching transactions for user {self.request.user.id}: {db_err}")
            # Return empty queryset on error to avoid crashing
            return Transaction.objects.none()

    def perform_create(self, serializer):
        try:
            # pass request context so serializer knows the user
            serializer.save()
        except DatabaseError as db_err:
            logger.error(f"Database error while creating transaction for user {self.request.user.id}: {db_err}")
            raise
        except Exception as exc:
            logger.exception(f"Unexpected error while creating transaction for user {self.request.user.id}")
            raise


class QueryTransactionListView(generics.ListAPIView):
    """
    GET /api/transactions/filter/

    Allows an authenticated user to query and filter their transaction records.

    Available query parameters:
    - stock:        Filter by stock symbol (case-insensitive exact match)
    - transaction_type:      Filter by transaction type ('BUY' or 'SELL')
    - date_after:   Filter transactions from this date onward (YYYY-MM-DD)
    - date_before:  Filter transactions up to this date (YYYY-MM-DD)
    - min_price:    Filter transactions where price_each >= min_price
    - max_price:    Filter transactions where price_each <= max_price

    The results are automatically scoped to the authenticated user and ordered
    by timestamp in descending order (most recent first).
    """

    renderer_classes = [UserRenderer]
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.filter(user=user)
        query_params = self.request.query_params

        try:
            # Filter by stock symbol
            stock = query_params.get('stock')
            if stock:
                queryset = queryset.filter(stock__symbol__iexact=stock)

            # Filter by transaction type
            transaction_type = query_params.get('transaction_type')
            if transaction_type:
                if transaction_type.upper() not in ['BUY', 'SELL']:
                    raise ValueError("transaction_type must be 'BUY' or 'SELL'.")
                queryset = queryset.filter(transaction_type__iexact=transaction_type)

            # Filter by date range
            date_after = query_params.get('date_after')
            date_before = query_params.get('date_before')

            # Validate and parse dates
            date_format = "%Y-%m-%d"
            if date_after:
                try:
                    date_after_parsed = datetime.strptime(date_after, date_format).date()
                except ValueError:
                    raise ValueError(f"Invalid date_after format. Expected YYYY-MM-DD.")

            if date_before:
                try:
                    date_before_parsed = datetime.strptime(date_before, date_format).date()
                except ValueError:
                    raise ValueError(f"Invalid date_before format. Expected YYYY-MM-DD.")

            if date_after and date_before:
                queryset = queryset.filter(timestamp__date__range=[date_after_parsed, date_before_parsed])
            elif date_after:
                queryset = queryset.filter(timestamp__date__gte=date_after_parsed)
            elif date_before:
                queryset = queryset.filter(timestamp__date__lte=date_before_parsed)

            # Filter by price range
            min_price = query_params.get('min_price')
            if min_price is not None:
                try:
                    min_price_val = float(min_price)
                    queryset = queryset.filter(price_each__gte=min_price_val)
                except ValueError:
                    raise ValueError("min_price must be a number.")

            max_price = query_params.get('max_price')
            if max_price is not None:
                try:
                    max_price_val = float(max_price)
                    queryset = queryset.filter(price_each__lte=max_price_val)
                except ValueError:
                    raise ValueError("max_price must be a number.")

            return queryset.order_by('-timestamp')

        except ValueError as ve:
           
            logger.warning(f"Validation error in UserTransactionListView: {ve} | User ID: {user.id}")
            raise

        except DatabaseError as db_err:
            logger.error(f"Database error in UserTransactionListView for user {user.id}: {db_err}")
   
            return Transaction.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except ValueError as ve:
            return Response(
                {"error": str(ve)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            logger.exception(f"Unexpected error listing transactions for user {request.user.id}: {exc}")
            return Response(
                {"error": "An unexpected error occurred while retrieving transactions."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

