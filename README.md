# Obsidian Store - Premium E-Commerce Website

A premium, modern e-commerce web application built using **Python**, **Flask**, **SQLite**, and **Docker**. It features a stunning glassmorphic dark theme, responsive grid systems, interactive AJAX cart actions, and a full administrator control panel.

---

## Key Features
- **Modern Obsidian Design**: Custom dark-themed layout built with fluid gradients, glowing borders, smooth card transitions, and custom-designed elements.
- **Dynamic Shopping Cart**: Full cart control using asynchronous AJAX. Add, modify quantities, and remove items with real-time subtotal and total calculations without page reloads.
- **Seeded Catalog**: Includes a database seeding system that automatically populates the shop with premium devices (custom keycaps, headsets, lighting) and high-quality generated product photos.
- **Secure Authentication**: Register and login with secure salted password hashing (`werkzeug.security`) and sticky login sessions (`Flask-Login`).
- **Complete Checkout System**: Order forms, stock limit verification, cart clear, and custom customer order history logging.
- **Administrator Panel**: Real-time sales telemetry dashboard, full catalog product inventory CRUD capabilities (Add, Edit with image uploads, Delete), and customer order tracking pipelines (Status: Pending, Paid, Shipped, Completed, Cancelled).
- **Docker Production Ready**: Single container `Dockerfile` (optimized multi-stage-like build) and `docker-compose.yml` with persistent Docker volumes for the database and product media.

---

## Default Accounts (Seeded)
When the app launches for the first time, it seeds the following testing credentials automatically:

### 1. Customer User
- **Username**: `user`
- **Password**: `userpassword`
- **Role**: Buyer (Catalog, Cart, Checkout, Order logs)

### 2. Administrator User
- **Username**: `admin`
- **Password**: `adminpassword`
- **Role**: Store Manager (Dashboard statistics, Product CRUD, Order Status modifications)

---

## Local Setup (Without Docker)
If you have **Python 3.10+** installed locally:

1. Clone or download this project.
2. Initialize virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run application:
   ```bash
   flask run
   ```
   *Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.*

---

## Docker Setup (With Docker Desktop)
To run the self-contained store with persistence:

1. Build and run containers:
   ```bash
   docker compose up -d --build
   ```
2. Access the store at [http://localhost:5000](http://localhost:5000).
3. Stop the container without losing database records:
   ```bash
   docker compose down
   ```
   *SQLite data and file uploads are preserved inside named volumes `db_data` and `uploads_data`.*

---

## Deploy to Render with Docker
To deploy this application to **Render.com** as described in the AppSignal reference guide:

1. **Commit Code to GitHub**:
   Push this project directory to a public or private GitHub repository.

2. **Create a Web Service on Render**:
   - Log in to your [Render Dashboard](https://dashboard.render.com/).
   - Click **New +** and select **Web Service**.
   - Connect your GitHub repository containing this project.

3. **Configure Settings**:
   - **Name**: `obsidian-store`
   - **Region**: Select closest to your customers.
   - **Branch**: `main` (or matching your default branch).
   - **Runtime**: Select **Docker**. (Render will automatically detect the `Dockerfile` in the root).

4. **Set Environment Variables**:
   Under the **Environment** tab on Render, add:
   - `SECRET_KEY` = *[Generate a long random secure string]*
   - `DATABASE_URL` = `sqlite:////workspace/instance/database.db`

5. **Deploy**:
   Render will build the Docker container and start Gunicorn. Once finished, you will receive a free public URL (e.g., `https://obsidian-store.onrender.com`).
