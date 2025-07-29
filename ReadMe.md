# Plagiarism Detection API

This is a FastAPI-based web application for plagiarism detection. It includes user management, subscription plans, document uploads, plagiarism reports, notifications, and admin functionality.

## Features

- User registration and login (JWT-based authentication)
- Token refresh and "Remember Me" support
- Role-based access (admin and user)
- Document upload and plagiarism check
- Subscription plan management
- Payment integration
- Resource (reference) management
- Audit logging
- Notifications
- Guest uploads with restrictions

## Technologies Used

- **Backend:** FastAPI, Python
- **Database:** PostgreSQL
- **Authentication:** JWT
- **Environment Management:** `dotenv`
- **Password Hashing:** `passlib[bcrypt]`
- **Database Connection:** `psycopg2`

## Project Structure

app/
│
├── algorithm/ # Plagiarism detection logic
├── controllers/ # Core business logic (users, payments, etc.)
├── database/ # DB connection, table creation, seeding
├── models/ # Pydantic models
├── routes/ # API endpoints
├── seed/ # Initial seed data (e.g., admin user)
├── utils/ # Utility functions (e.g., JWT handler)
│
main.py # FastAPI app initialization and router setup

## Environment Variables (`.env`)

DB_HOST=localhost
DB_PORT=5432
DB_NAME=plagiarism_db
DB_USER=your_user
DB_PASSWORD=your_password

JWT_SECRET=your_jwt_secret
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

PORT=8000

## Create a virtual environment:
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

## Install dependencies:
pip install -r requirements.txt

## Run the application:
uvicorn main:app --reload

## Key Endpoints
## Users
POST /users/register – Register a new user

POST /users/login – Login and get tokens

GET /users/me – Get current user info (requires token)

## Resources
POST /upload – Upload a document and check for plagiarism

## Plans, Payments, Reports, etc.
Accessible under /plans, /payments, /reports, etc., depending on roles

## Guest Restrictions
 -Guests can upload up to 5 .txt files under 1000 words
 -Other file types and unlimited access require login and active subscription


