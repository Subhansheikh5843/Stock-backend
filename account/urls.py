from django.urls import path
from .views import *
urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('ingest-stocks/', IngestStocksView.as_view(), name='ingest-stocks'),
    path('query-stocks/', StockQueryView.as_view(), name='stock-query'),
    path('transactions/', TransactionView.as_view(), name='transactions'),
    path('query-transactions/', QueryTransactionListView.as_view(), name='query-transactions'),
]