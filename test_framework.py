import unittest
import os
import sqlite3
import hashlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.arima.model import ARIMA
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error

class TestInventoryMLFramework(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_users.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        self.conn = sqlite3.connect(self.test_db)
        cur = self.conn.cursor()
        cur.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                question TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def test_user_registration_and_login(self):
        cur = self.conn.cursor()
        username = "ranga"
        email = "chinnusreeram413@gmail.com"
        password = "Ranga@123"
        pw_hash = self.hash_password(password)

        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, pw_hash)
        )
        self.conn.commit()

        cur.execute("SELECT username, email FROM users WHERE (username = ? OR email = ?) AND password = ?",
                    (username, username, pw_hash))
        user = cur.fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user[0], "ranga")
        self.assertEqual(user[1], "chinnusreeram413@gmail.com")

    def test_password_reset(self):
        cur = self.conn.cursor()
        username = "ranga"
        email = "chinnusreeram413@gmail.com"
        old_pw = self.hash_password("OldPassword123")
        cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, old_pw))
        self.conn.commit()

        new_pw = self.hash_password("NewRangaSecret456")
        cur.execute("UPDATE users SET password = ? WHERE LOWER(username) = LOWER(?)", (new_pw, username))
        self.conn.commit()

        cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        self.assertEqual(row[0], new_pw)

    def test_inventory_stock_calculations(self):
        # Demand: array of daily demand values
        demand = np.array([120, 150, 130, 170, 140, 160, 155, 145, 150, 165])
        lead_time = 7  # days
        z_score = 1.65  # 95% service level

        avg_demand = demand.mean()
        std_demand = demand.std()
        expected_safety_stock = z_score * std_demand * np.sqrt(lead_time)
        expected_rop = (avg_demand * lead_time) + expected_safety_stock

        self.assertGreater(expected_safety_stock, 0)
        self.assertGreater(expected_rop, expected_safety_stock)
        self.assertAlmostEqual(avg_demand, 148.5, places=1)

    def test_linear_regression_pipeline(self):
        np.random.seed(42)
        days = np.arange(1, 101).reshape(-1, 1)
        sales = 50 + 1.5 * days.flatten() + np.random.normal(0, 5, 100)

        lr = LinearRegression()
        lr.fit(days[:80], sales[:80])
        preds = lr.predict(days[80:])

        mae = mean_absolute_error(sales[80:], preds)
        rmse = np.sqrt(mean_squared_error(sales[80:], preds))
        self.assertLess(mae, 15)
        self.assertLess(rmse, 18)

    def test_random_forest_pipeline(self):
        np.random.seed(42)
        days = np.arange(1, 101).reshape(-1, 1)
        sales = 100 + np.sin(days.flatten() / 5) * 20 + np.random.normal(0, 3, 100)

        rf = RandomForestRegressor(n_estimators=50, random_state=42)
        rf.fit(days[:80], sales[:80])
        preds = rf.predict(days[80:])

        mae = mean_absolute_error(sales[80:], preds)
        self.assertLess(mae, 15)

    def test_arima_pipeline(self):
        series = pd.Series([100 + i + (i % 5) for i in range(50)])
        model = ARIMA(series[:40], order=(1, 1, 1))
        fitted = model.fit()
        forecast = fitted.forecast(steps=10)
        self.assertEqual(len(forecast), 10)
        self.assertFalse(np.isnan(forecast).any())

    def test_neural_network_pipeline(self):
        series = np.array([50 + i * 2 + (i % 3) * 5 for i in range(40)])
        time_steps = 4
        X_seq, y_seq = [], []
        for i in range(len(series) - time_steps):
            X_seq.append(series[i:i + time_steps])
            y_seq.append(series[i + time_steps])
        X_seq, y_seq = np.array(X_seq), np.array(y_seq)
        
        mlp = MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=300, random_state=42)
        mlp.fit(X_seq[:28], y_seq[:28])
        preds = mlp.predict(X_seq[28:])
        self.assertEqual(len(preds), len(y_seq[28:]))
        self.assertFalse(np.isnan(preds).any())

    def test_datasets_exist_and_readable(self):
        dataset_files = [
            os.path.join("Datasets", "customer_info.csv"),
            os.path.join("Datasets", "sales_cars.csv"),
            os.path.join("Datasets", "Sample - Superstore.xlsx"),
            os.path.join("Datasets", "Inventory_data.xlsx")
        ]
        for path in dataset_files:
            self.assertTrue(os.path.exists(path), f"File {path} does not exist.")
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            self.assertGreater(len(df), 0, f"File {path} is empty.")

if __name__ == "__main__":
    unittest.main()
