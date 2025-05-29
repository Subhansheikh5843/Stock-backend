
## Project Overview

This is a Django-based backend API for managing user accounts, stock data ingestion, stock querying, and transaction tracking. It uses JWT authentication and is fully dockerized with PostgreSQL.

---

## Features

* **User Registration & Login** via JWT
* **Admin-only** stock data ingestion
* **Stock Querying** with filters and ordering
* **Transaction Management** (BUY/SELL) with balance updates
* **Protected Endpoints** with role-based access
* **Comprehensive Error Handling** and logging

---




## Getting Started

### Clone Repository

```bash
git clone https://github.com/Subhansheikh5843/Stock-backend.git

```

### Environment Variables

Copy the example file and adjust values:

```bash
cp .envExample .env
```

**.envExample**:

```
DATABASE_NAME=mydb1
DATABASE_USER=myuser
DATABASE_PASSWORD=1234
DATABASE_HOST=postgres_db
DATABASE_PORT=5432
```

### Docker Compose

Run the following command to build and start all services:

```bash
docker compose up --build
```

This will:

1. Build the Django `web` service
2. Start the PostgreSQL `postgres_db` service (exposed on host port 5432)
3. Apply database migrations and launch the Django development server on port 8000

To tear down and remove volumes (forcing a fresh Postgres init):

```bash
docker compose down -v
```

---

## Authentication & Superuser Setup

All protected endpoints require a Bearer token in the **Authorization** header.

1. **Register** a new user or **login** to receive your **access** and **refresh** tokens.
2. For **admin-only** endpoints (e.g. **ingest-stocks**), you must first create a superuser inside the running container:

```bash
   docker compose exec web sh
   python manage.py createsuperuser
```

   Then **login** as that superuser via Postman to obtain the superuser token for the admin endpoints.
---

## API Endpoints

All endpoints are prefixed with `/api/user/` and expect JSON bodies.

### Authentication
### Register a new user               
 POST    `http://127.0.0.1:8000/api/user/register/`     
 #### Inputs   
`{
  "email":        "example@gmail.com",
  "name":         "name",
  "current_balance":7486,
  "password":     "pass",
  "password2":    "pass",
  "tc":           true
}`
 #### Outputs
  `{ token: { access, refresh }, msg }`

### Login 
 POST    `http://127.0.0.1:8000/api/user/login/`   
#### Inputs 
`{
  "email":        "example@gmail.com",
  "password":     "pass"

}` 
 #### Outputs                
`{ token: { access, refresh }, msg }` 



### Stock Management

**Ingest Stocks (Admin Only)**

1. In Postman, set **Authorization** to **Bearer Token** and paste your **superuser** `Bearer access_token`.
2. Create a **GET** request to `http://127.0.0.1:8000/api/user/ingest-stocks/` and send.       

**Query Stocks (User)**

1. Set **Authorization** to your regular user `Bearer access_token`.
2. Create a **GET** request to `http://127.0.0.1:8000/api/user/query-stocks/`.

 `http://127.0.0.1:8000/api/user/query-stocks?symbol=AAPL`
` http://127.0.0.1:8000/api/user/query-stocks?min_price=100&max_price=500`
` http://127.0.0.1:8000/api/user/query-stocks?symbol=TSLA&min_price=500&ordering=updated_at`
` http://127.0.0.1:8000/api/user/query-stocks?ordering=-last_price  `

### Transactions

**List Transactions**

1. Set **Authorization** to your `Bearer access_token`.
2. Create a **GET** request to `http://127.0.0.1:8000/api/user/transactions/` and send.`                                                                                           
 
**Create Transaction**

1. Set **Authorization** to your `Bearer access_token`.
2. Create a **POST** request to `http://127.0.0.1:8000/api/user/transactions/`.
3. Under **Body**, choose **raw** + **JSON** and enter:

   ```json
   {
     "stock": "MSFT",
     "tx_type": "BUY",
     "quantity": 4,
     "price_each": "310.00"
   }
   ```
  ```json
   {
  "stock": "MSFT",
  "tx_type": "SELL",
  "quantity": 3,
  "price_each": "310.00"
    }
   ```

4. Send the request.


**Query Transactions**

1. Set **Authorization** to your `Bearer access_token`.
2. Create a **GET** request to `http://127.0.0.1:8000/api/user/query-transactions/`.
3. Under **Params**, add filters like `stock=MSFT`, `tx_type=SELL`, `date_after=2025-01-01`, `min_price=100`. 

` http://127.0.0.1:8000/api/user/query-transactions/?stock=MSFT`
` http://127.0.0.1:8000/api/user/query-transactions/?tx_type=SELL`
` http://127.0.0.1:8000/api/user/query-transactions/??date_after=2025-01-01&date_before=2025-12-31`
` http://127.0.0.1:8000/api/user/query-transactions/?min_price=100&max_price=400`
` http://127.0.0.1:8000/api/user/query-transactions/?stock=MSFT&tx_type=SELL&date_a`

---

### Testing with Postman

Register a user via the Register endpoint and obtain your access and refresh tokens from the JSON response.

Login with the same credentials to retrieve tokens again if needed.

For any protected endpoint, under Postman’s Authorization tab select `Bearer Token` and paste your access token.

Invoke the desired endpoints (/load-stocks, /query-stocks, /transactions, /query-transactions) with the correct token.

For the admin-only `/ingest-stocks` endpoint, be sure to use the superuser token obtained by creating a superuser inside the container (docker-compose exec web sh → python manage.py createsuperuser).

---
