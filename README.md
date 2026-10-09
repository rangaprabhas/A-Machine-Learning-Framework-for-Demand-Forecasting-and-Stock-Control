# A Machine Learning Framework for Demand Forecasting and Stock Control 📈⚙️

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39.0-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.4.2-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-ready machine learning framework designed to predict future product demand, optimize safety stock levels, compute reorder points, and assist supply chain decision-makers in eliminating stockouts while minimizing holding costs.

---

## 🌟 Key Features

- **Robust User Authentication & Security:**
  - Secure registration, login, and password reset workflows backed by an embedded SQLite database.
  - Password encryption using SHA-256 hashing with salting.
  - Session state persistence for seamless page routing.

- **Dynamic Stock Control & Inventory Optimization:**
  - **Lead Time Demand ($LTD$):** Estimates inventory requirements across supplier delivery lead times.
  - **Safety Stock ($SS$):** Quantifies buffer stock under a 95% service level factor ($Z = 1.65$) to absorb demand volatility.
  - **Reorder Point ($ROP$):** Generates actionable inventory replenishment alerts and minimum stock thresholds.

- **Multi-Model Machine Learning Forecasting Suite:**
  - **Linear Regression:** Establishes trend baselines across seasonal ordinal cycles.
  - **Random Forest Regressor:** Captures non-linear shocks, market trends, and demand spikes.
  - **ARIMA (AutoRegressive Integrated Moving Average):** Statistical time series model for stationary and differenced demand cycles.
  - **LSTM (Long Short-Term Memory Neural Networks):** Deep learning architecture capturing sequential multi-period dependencies.

- **Interactive Visualizations & Analytics:**
  - Actual vs. Predicted scatter validation with ideal 1:1 fit reference indicators.
  - Multi-day forward forecast curves rendered dynamically with Plotly.
  - Instant CSV export for downstream ERP or spreadsheet integration.

- **Flexible Data Intake & Built-in Benchmark Datasets:**
  - Upload up to 5 CSV or Excel (`.xlsx`) datasets concurrently.
  - Automatic column detection for date dimensions and sales/demand metrics.
  - One-click sample dataset loader including Superstore Sales, Automotive Sales, and Inventory logs.

---

## 🏗️ Repository Architecture

```text
├── .streamlit/
│   └── config.toml          # Streamlit theme & server configuration
├── Datasets/
│   ├── customer_info.csv    # Benchmark customer profile records
│   ├── Inventory_data.xlsx  # Multi-category inventory benchmark
│   ├── product.xlsx         # Catalog benchmark
│   ├── sales_cars.csv       # Automotive sales time series
│   ├── Sample - Superstore.xlsx # Retail demand benchmark
│   └── train.xlsx           # Historical demand records
├── ML_project_main.py       # Core application engine & UI controller
├── test_framework.py        # Automated unit test suite
├── requirements.txt         # Production dependencies
├── users_data.db            # Local SQLite authentication database
├── README.md                # Project documentation
├── config.toml              # Backup server configuration
└── assets / icons           # UI logos, icons, and media files
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10 or 3.11
- Git

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone <YOUR_REPOSITORY_URL>
cd <REPOSITORY_NAME>
pip install -r requirements.txt
```

### 3. Launch Application

Start the Streamlit application server:

```bash
streamlit run ML_project_main.py
```

Open your browser at `http://localhost:8501`.

---

## 🔑 Default Credentials

For quick evaluation and demonstration, the application is pre-seeded with the following administrator credentials:

- **Username:** `ranga`
- **Email:** `chinnusreeram413@gmail.com`
- **Password:** `Ranga@123`

*You may also create a new account or utilize the "Forgot Password" self-service reset page at any time.*

---

## 🧪 Testing and Verification

Run the automated test suite covering database operations, stock formulas, and ML model training:

```bash
python -m unittest test_framework.py -v
```

---

## 📐 Mathematical Formulation

### Inventory Optimization Formulas

1. **Lead Time Demand ($LTD$):**
   $$\text{LTD} = \bar{D} \times L$$
   *where $\bar{D}$ is the average daily demand and $L$ is supplier lead time in days.*

2. **Safety Stock ($SS$):**
   $$SS = Z \times \sigma_D \times \sqrt{L}$$
   *where $Z = 1.65$ represents a 95% service level factor and $\sigma_D$ is the standard deviation of daily demand.*

3. **Reorder Point ($ROP$):**
   $$ROP = \text{LTD} + SS = (\bar{D} \times L) + SS$$

---

## 👤 Author & Attribution

- **Lead Developer & Maintainer:** Ranga
- **License:** Licensed under the [MIT License](LICENSE).
