import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error
import plotly.graph_objects as go
import plotly.express as px
import sqlite3
import hashlib
import time
import chardet
import warnings
warnings.filterwarnings("ignore")

try:
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
except ImportError:
    try:
        from keras.callbacks import EarlyStopping
        from keras.models import Sequential
        from keras.layers import LSTM, Dense
    except ImportError:
        pass

# Page Configuration
st.set_page_config(
    page_title="A Machine Learning Framework for Demand Forecasting and Stock Control",
    layout="wide",
    page_icon="icon2.png",
    initial_sidebar_state="expanded"
)

# SQLite Database Helper Functions
DB_FILE = "users_data.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            question TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ensure default user exists
    cur.execute("SELECT 1 FROM users WHERE username = ?", ("ranga",))
    if cur.fetchone() is None:
        pw_hash = hashlib.sha256("Ranga@123".encode()).hexdigest()
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            ("ranga", "chinnusreeram413@gmail.com", pw_hash)
        )
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def user_exists(email=None, username=None):
    conn = get_connection()
    cur = conn.cursor()
    if email:
        cur.execute("SELECT 1 FROM users WHERE LOWER(email) = LOWER(?)", (email,))
    elif username:
        cur.execute("SELECT 1 FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def register_user(username, email, password):
    if not email or not password or not username:
        return False, "Username, email, and password are required."
    if user_exists(email=email):
        return False, "This email is already registered."
    if user_exists(username=username):
        return False, "This username is already taken."
    
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), hash_password(password))
        )
        conn.commit()
        conn.close()
        return True, "Account registered successfully."
    except Exception as e:
        return False, f"Database error: {e}"

def reset_user_password(identifier, new_password):
    if not identifier or not new_password:
        return False, "Identifier and new password are required."
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)",
            (identifier.strip(), identifier.strip())
        )
        user = cur.fetchone()
        if not user:
            conn.close()
            return False, "No account found matching that username or email."
        
        cur.execute(
            "UPDATE users SET password = ? WHERE id = ?",
            (hash_password(new_password), user[0])
        )
        conn.commit()
        conn.close()
        return True, "Password has been updated successfully."
    except Exception as e:
        return False, f"Error updating password: {e}"

def validate_login(identifier, password):
    if not identifier or not password:
        return None
    conn = get_connection()
    cur = conn.cursor()
    hashed = hash_password(password)
    cur.execute(
        "SELECT username, email FROM users WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)) AND password = ?",
        (identifier.strip(), identifier.strip(), hashed)
    )
    user = cur.fetchone()
    conn.close()
    return user

# Initialize Database Schema
init_db()

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "show_data" not in st.session_state:
    st.session_state.show_data = False   
if "username" not in st.session_state:
    st.session_state.username = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Custom UI Theme & CSS Styling
st.markdown("""
    <style>
        :root {
            --brand-primary: #2563EB;
            --brand-secondary: #1E40AF;
            --brand-accent: #059669;
            --card-bg: #FFFFFF;
            --text-dark: #0F172A;
            --text-muted: #64748B;
            --border-color: #E2E8F0;
        }

        /* Typography & Spacing */
        h1, h2, h3, h4, h5, h6 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-weight: 700;
            color: var(--text-dark);
            letter-spacing: -0.02em;
        }

        /* Hero Banner Container */
        .hero-container {
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #3B82F6 100%);
            color: #FFFFFF;
            padding: 30px;
            border-radius: 14px;
            margin-bottom: 25px;
            box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
        }
        .hero-badge {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 12px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .hero-title {
            color: #FFFFFF !important;
            font-size: 2rem;
            font-weight: 800;
            margin: 0 0 10px 0;
            line-height: 1.25;
        }
        .hero-subtitle {
            color: #E0E7FF;
            font-size: 1.05rem;
            margin: 0;
            max-width: 800px;
        }

        /* Metric & Feature Cards */
        .metric-card {
            background-color: #F8FAFC;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--brand-primary);
        }
        .metric-label {
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 5px;
        }

        /* Style for tabs */
        div[data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F1F5F9;
            padding: 6px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        div[data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 0.95rem;
            color: #475569;
            border: none;
            background: transparent;
        }
        div[role="tab"][aria-selected="true"] {
            background-color: #FFFFFF !important;
            color: #2563EB !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
        }

        /* Buttons & Inputs */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            border-color: var(--brand-primary);
            box-shadow: 0 4px 10px rgba(37, 99, 235, 0.15);
        }

        /* Sidebar user badge */
        .user-badge {
            background: #EFF6FF;
            border-left: 4px solid #2563EB;
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

def signup_page():
    st.markdown("""
        <div style="max-width: 500px; margin: 30px auto; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="margin-top: 0; color: #1E3A8A; text-align: center;">Create Your Account</h2>
            <p style="text-align: center; color: #64748B; font-size: 0.95rem;">Join the AI Demand Forecasting & Stock Control Framework</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("signup_form"):
            username = st.text_input("Username *", placeholder="e.g. ranga")
            email = st.text_input("Email *", placeholder="you@example.com")
            password = st.text_input("Password *", type="password")
            confirm = st.text_input("Confirm Password *", type="password")
            submitted = st.form_submit_button("Sign Up", use_container_width=True)
            
            if submitted:
                if password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif not email or not username:
                    st.error("Please fill in all required fields.")
                else:
                    success, msg = register_user(username, email, password)
                    if success:
                        st.success("Account created successfully! Redirecting to login...")
                        time.sleep(1.2)
                        st.session_state.current_page = "login"
                        st.rerun()
                    else:
                        st.error(msg)

        if st.button("Already have an account? Log In", use_container_width=True):
            st.session_state.current_page = "login"
            st.rerun()

def reset_password_page():
    st.markdown("""
        <div style="max-width: 500px; margin: 30px auto; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h2 style="margin-top: 0; color: #1E3A8A; text-align: center;">Reset Password</h2>
            <p style="text-align: center; color: #64748B; font-size: 0.95rem;">Enter your username or email to set a new password</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("reset_password_form"):
            identifier = st.text_input("Username or Registered Email *", placeholder="Enter username or email")
            new_password = st.text_input("New Password *", type="password")
            confirm_new_password = st.text_input("Confirm New Password *", type="password")
            reset_button = st.form_submit_button("Update Password", use_container_width=True)

            if reset_button:
                if not identifier:
                    st.error("Please provide your username or email.")
                elif len(new_password) < 6:
                    st.error("New password must be at least 6 characters long.")
                elif new_password != confirm_new_password:
                    st.error("New passwords do not match.")
                else:
                    success, msg = reset_user_password(identifier, new_password)
                    if success:
                        st.success(f"{msg} Redirecting to login...")
                        time.sleep(1.5)
                        st.session_state.current_page = "login"
                        st.rerun()
                    else:
                        st.error(msg)

        if st.button("← Back to Login", use_container_width=True):
            st.session_state.current_page = "login"
            st.rerun()

def login_page():
    st.markdown("""
        <div style="max-width: 520px; margin: 35px auto 20px auto; padding: 30px 25px; border-radius: 14px; border: 1px solid #E2E8F0; background: #FFFFFF; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); text-align: center;">
            <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 12px;">
                <span style="font-size: 2.2rem;">📊</span>
            </div>
            <h2 style="margin: 0 0 8px 0; color: #1E3A8A; font-weight: 800;">Framework Portal</h2>
            <p style="color: #64748B; font-size: 0.95rem; margin: 0;">Sign in to access Demand Forecasting & Stock Control</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form(key='login_form'):
            username_or_email = st.text_input("Username or Email", placeholder="e.g. ranga or chinnusreeram413@gmail.com")
            password = st.text_input("Password", type='password', placeholder="Enter your password")
            login_button = st.form_submit_button("Sign In", use_container_width=True)

            if login_button:
                user = validate_login(username_or_email, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user[0] or "Ranga"
                    st.session_state.user_email = user[1]
                    st.success(f"Welcome back, {st.session_state.username}!")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Incorrect username, email, or password.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create Account", use_container_width=True):
                st.session_state.current_page = "signup"   
                st.rerun() 
        with c2:
            if st.button("Forgot Password?", use_container_width=True):
                st.session_state.current_page = "reset"
                st.rerun()

def toggle_data_visibility():
    st.session_state.show_data = not st.session_state.show_data

# Main Application Dashboard
def app(): 
    # Hero Banner
    st.markdown("""
        <div class="hero-container">
            <span class="hero-badge">Machine Learning Framework</span>
            <h1 class="hero-title">A Machine Learning Framework for Demand Forecasting and Stock Control</h1>
            <p class="hero-subtitle">Optimize inventory reorder levels, predict sales trajectory with regression & deep learning models, and streamline supply chain decisions.</p>
        </div>
    """, unsafe_allow_html=True)

    # Developer & Default Factors Overview
    with st.expander("Explore Reference Datasets (Holidays, Weather, Customer Profiles)", expanded=False):
        data = {
            'Date': [
                '2024-01-01', '2024-01-13', '2024-01-13', '2024-04-26', 
                '2024-03-08', '2024-04-02', '2024-04-10', '2024-04-17', 
                '2024-05-03', '2024-07-13', '2024-07-17', '2024-08-19', 
                '2024-09-07', '2024-09-08', '2024-10-12', '2024-10-02', 
                '2024-10-31', '2024-11-15', '2024-12-25', '2024-08-15'
            ],
            'Holiday Name': [
                'New Year', 'Lohri', 'Makar Sankranti', 'Republic Day', 
                'Shivratri', 'Ugadi', 'Rama Navami', 'Good Friday', 
                'Ramzan Id/Eid-ul-Fitar', 'Bakr Id/Eid ul-Adha', 'Muharram', 
                'Janmashtami', 'Ganesh Chaturthi', 'Onam', 
                'Mahatma Gandhi Jayanti', 'Navratri', 
                'Diwali', 'Guru Nanak Jayanti', 'Christmas', 
                'Independence Day'
            ],
            'Holiday Impact': [
                'High', 'Medium', 'Low', 'High', 
                'Low', 'Medium', 'Low', 'High', 
                'Low', 'Medium', 'Low', 'High', 
                'High', 'Low', 'High', 'Medium', 
                'Low', 'High', 'Medium', 'Low'
            ],
            'Weather Condition': [
                'Fog', 'Sunny', 'Humid', 'Cloudy', 
                'Sunny', 'Partly Cloudy', 'Clear', 'Clear', 
                'Sunny', 'Sunny', 'Fog', 'Cloudy', 
                'Sunny', 'Sunny', 'Fog', 'Cloudy', 
                'Clear', 'Sunny', 'Sunny', 'Sunny'
            ],
            'Temperature (°C)': [
                17, 25, 23, 19, 27, 22, 30, 29, 21, 31, 25, 24, 28, 29, 22, 21, 30, 28, 25, 26
            ],
            'Weather Impact': [
                'Medium', 'Low', 'Medium', 'Low', 'Low', 'Low', 'Medium', 'Low', 
                'High', 'Low', 'Medium', 'Medium', 'Low', 'Medium', 'Low', 'Medium', 
                'Low', 'Medium', 'Low', 'Medium'
            ],
            'Promotion Name': [
                'Winter Sale', 'No Promotion', 'No Promotion', 'Republic Day Offer', 
                'No Promotion', 'Holi Festival Discount', 'No Promotion', 'No Promotion', 
                'Eid Celebration Discount', 'Independence Day Sale', 'No Promotion', 
                'No Promotion', 'Ganesh Chaturthi Promo', 'No Promotion', 
                'Onam Special Offer', 'No Promotion', 'Navratri Special', 
                'Diwali Discount', 'No Promotion', 'Christmas Bonanza'
            ],
            'Discount Percentage (%)': [
                10, 0, 0, 15, 0, 30, 0, 0, 35, 40, 0, 0, 25, 0, 40, 25, 50, 0, 50, 0
            ],
            'Promotion Impact': [
                'Medium', 'None', 'None', 'Medium', 'None', 'Medium', 'None', 'None', 
                'High', 'High', 'None', 'None', 'High', 'None', 'Medium', 'Medium', 
                'Very High', 'None', 'Very High', 'None'
            ]
        }
        external_factors_df = pd.DataFrame(data)
        external_factors_df['Date'] = pd.to_datetime(external_factors_df['Date'])

        customer_data = {
            'Customer ID': [1, 2, 3, 4, 5],
            'Customer Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
            'Age': [28, 34, 22, 45, 30],
            'Gender': ['Female', 'Male', 'Male', 'Male', 'Female'],
            'Location': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
            'Purchase History': ['Electronics', 'Clothing', 'Books', 'Grocery', 'Sports'],
            'Preferred Holidays': ['New Year', 'Christmas', 'Diwali', 'Independence Day', 'Lohri'],
            'Spending Habit': ['Medium', 'High', 'Low', 'Medium', 'High']
        }
        customer_info_df = pd.DataFrame(customer_data)

        col1, col2 = st.columns(2)
        with col1:
            st.write("#### External Factors (Seasonality & Promotions)")
            st.dataframe(external_factors_df, use_container_width=True)
        with col2:
            st.write("#### Customer Profiles & Demand Segment")
            st.dataframe(customer_info_df, use_container_width=True)

    # Data Upload & Quick Sample Loader
    st.subheader("Data Intake: Upload Datasets or Load Sample")
    
    loader_col1, loader_col2 = st.columns([2, 1])
    with loader_col1:
        uploaded_files = st.file_uploader(
            "Upload Sales / Inventory Datasets (CSV or Excel, up to 5 files)", 
            type=["csv", "xlsx"], 
            accept_multiple_files=True
        )
    with loader_col2:
        st.write("**Quick-Load Built-in Sample:**")
        sample_choice = st.selectbox(
            "Select sample data to inspect immediately:",
            ["None", "Superstore Sales (Excel)", "Automotive Sales (CSV)", "Inventory Records (Excel)"]
        )

    datasets = {}
    
    # Load user uploaded files
    if uploaded_files:
        if len(uploaded_files) > 5:
            st.error("Maximum 5 files can be processed simultaneously.")
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.size > 0:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            raw_data = uploaded_file.read(10000)
                            encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
                            uploaded_file.seek(0)
                            datasets[uploaded_file.name] = pd.read_csv(uploaded_file, encoding=encoding)
                        elif uploaded_file.name.endswith('.xlsx'):
                            datasets[uploaded_file.name] = pd.read_excel(uploaded_file)
                    except Exception as e:
                        st.error(f"Error loading {uploaded_file.name}: {e}")
                else:
                    st.error(f"{uploaded_file.name} is empty.")

    # Load sample file if selected and no files uploaded
    if not datasets and sample_choice != "None":
        sample_path = None
        if sample_choice == "Superstore Sales (Excel)":
            sample_path = os.path.join("Datasets", "Sample - Superstore.xlsx")
        elif sample_choice == "Automotive Sales (CSV)":
            sample_path = os.path.join("Datasets", "sales_cars.csv")
        elif sample_choice == "Inventory Records (Excel)":
            sample_path = os.path.join("Datasets", "Inventory_data.xlsx")
            
        if sample_path and os.path.exists(sample_path):
            try:
                name = os.path.basename(sample_path)
                if sample_path.endswith('.csv'):
                    datasets[name] = pd.read_csv(sample_path)
                else:
                    datasets[name] = pd.read_excel(sample_path)
                st.info(f"Loaded sample dataset: `{name}` ({len(datasets[name]):,} records)")
            except Exception as e:
                st.error(f"Error loading sample dataset: {e}")

    if datasets:
        st.markdown("---")
        st.subheader("Dataset Summary & Optimization Workbench")
        
        # Summary KPI Cards
        total_rows = sum([len(df) for df in datasets.values()])
        total_size = sum([df.memory_usage().sum() for df in datasets.values()])
        
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{len(datasets)}</div>
                    <div class="metric-label">Active Datasets Loaded</div>
                </div>
            """, unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_rows:,}</div>
                    <div class="metric-label">Total Combined Observations</div>
                </div>
            """, unsafe_allow_html=True)
        with kpi3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{total_size / (1024 ** 2):.2f} MB</div>
                    <div class="metric-label">Data In-Memory Footprint</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Dataset Tabs
        tab_titles = [f"Dataset {i+1}: {name[:20]}" for i, name in enumerate(datasets.keys())]
        tab_elements = st.tabs(tab_titles)

        possible_sales_columns = [
            'Sales', 'sales', 'SalesQuantity', 'salesquantity', 'quantity_sold', 'QuantitySold', 
            'quantitysold', 'ProjectedSales', 'projected_sales', 'TotalSales', 'totalsales', 
            'TotalQuantity', 'totalquantity', 'Quantity', 'quantity', 'ExpectedSales', 
            'HistoricalSales', 'Revenue', 'revenue', 'SalesRevenue', 'UnitsSold', 'unitssold', 
            'ItemsSold', 'itemssold', 'VolumeSold', 'Demand', 'demand', 'DemandQuantity', 
            'OrderQuantity', 'orderquantity', 'StockQuantity', 'RetailSales'
        ]

        possible_date_columns = [
            'date', 'datetime', 'timestamp', 'time', 'order date', 'Order Date', 'Order_Date', 
            'purchasedate', 'PurchaseDate', 'purchase date', 'Purchase Date', 'sale date', 
            'Sale Date', 'transaction date', 'Transaction Date', 'ship date', 'Ship Date', 
            'invoice date', 'Invoice Date', 'saledate', 'SalesDate'
        ]
        normalized_possible_dates = [c.lower().replace(' ', '_').replace('-', '_') for c in possible_date_columns]

        for index, (name, dataset) in enumerate(datasets.items()):
            with tab_elements[index]:
                st.write(f"### Analysis for `{name}`")
                
                with st.expander("Data Preview & Column Diagnostics", expanded=False):
                    st.dataframe(dataset.head(8), use_container_width=True)

                # Column detection
                sales_col = next((col for col in possible_sales_columns if col in dataset.columns), None)
                date_col = None
                for col in dataset.columns:
                    norm = col.lower().replace(' ', '_').replace('-', '_')
                    if norm in normalized_possible_dates:
                        date_col = col
                        break

                col_a, col_b = st.columns(2)
                with col_a:
                    if sales_col:
                        st.success(f"Detected Demand/Sales Metric: **`{sales_col}`**")
                        dataset.rename(columns={sales_col: 'Sales'}, inplace=True)
                    else:
                        st.error("No standard Sales/Demand column automatically detected.")
                        numeric_cols = dataset.select_dtypes(include=[np.number]).columns.tolist()
                        if numeric_cols:
                            manual_sales = st.selectbox("Select numeric column to use as Sales/Demand:", numeric_cols, key=f"manual_sales_{index}")
                            dataset['Sales'] = dataset[manual_sales]
                            sales_col = 'Sales'
                
                with col_b:
                    if date_col:
                        st.success(f"Detected Temporal Dimension: **`{date_col}`**")
                    else:
                        date_candidates = [c for c in dataset.columns if 'date' in c.lower() or 'time' in c.lower() or 'day' in c.lower()]
                        if date_candidates:
                            date_col = st.selectbox("Select temporal/date column:", date_candidates, key=f"manual_date_{index}")
                        else:
                            st.warning("No explicit date column found; synthetic timeline index will be assigned.")
                            dataset['Date'] = pd.date_range(start='2024-01-01', periods=len(dataset), freq='D')
                            date_col = 'Date'

                if 'Sales' in dataset.columns:
                    # Clean sales numbers
                    dataset['Sales'] = pd.to_numeric(dataset['Sales'], errors='coerce').fillna(0)

                    # Section 1: Stock Control & Inventory Optimization
                    st.markdown("#### 1. Inventory Stock Control & Optimization")
                    
                    c_opt1, c_opt2 = st.columns([1, 1])
                    with c_opt1:
                        safety_stock_level = st.slider(
                            "Safety Stock Threshold (Units)", 
                            min_value=10, 
                            max_value=2000, 
                            value=300, 
                            step=10,
                            key=f"safety_stock_{name}"
                        )
                        lead_time = st.slider(
                            "Supplier Lead Time (Days)", 
                            min_value=1, 
                            max_value=30, 
                            value=7, 
                            key=f"lead_time_{name}"
                        )

                    dataset['Stock Status'] = np.where(dataset['Sales'] < safety_stock_level, "Restock Required", "Sufficient Stock")

                    # Inventory calculations
                    avg_daily_demand = dataset['Sales'].mean()
                    std_daily_demand = dataset['Sales'].std()
                    z_service_level = 1.65  # 95% service level
                    recommended_safety_stock = z_service_level * (std_daily_demand * np.sqrt(lead_time)) if std_daily_demand > 0 else 0
                    reorder_point = (avg_daily_demand * lead_time) + recommended_safety_stock

                    with c_opt2:
                        st.markdown(f"""
                            <div style="background: #F1F5F9; padding: 15px; border-radius: 10px; border-left: 4px solid #2563EB;">
                                <h5 style="margin: 0 0 8px 0; color: #1E3A8A;">Stock Control Recommendations</h5>
                                <p style="margin: 4px 0;"><strong>Average Daily Demand:</strong> {avg_daily_demand:.2f} units</p>
                                <p style="margin: 4px 0;"><strong>Demand Volatility (Std Dev):</strong> {std_daily_demand:.2f}</p>
                                <p style="margin: 4px 0;"><strong>Recommended Safety Stock (95% SL):</strong> {recommended_safety_stock:.2f} units</p>
                                <p style="margin: 4px 0; font-size: 1.1rem; color: #B91C1C;"><strong>Recommended Reorder Point (ROP):</strong> {reorder_point:.2f} units</p>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Section 2: Machine Learning Demand Forecasting
                    st.markdown("#### 2. Machine Learning Demand Forecasting")

                    # Process Date
                    dataset[date_col] = pd.to_datetime(dataset[date_col], errors='coerce')
                    dataset = dataset.dropna(subset=[date_col]).sort_values(by=date_col)
                    dataset['DayOfYear'] = dataset[date_col].dt.dayofyear.fillna(1).astype(int)

                    X = dataset[['DayOfYear']]
                    y = dataset['Sales']

                    if len(dataset) < 15:
                        st.warning("Dataset contains fewer than 15 valid records. Predictions require more history for optimal statistical confidence.")

                    f_col1, f_col2 = st.columns([1, 1])
                    with f_col1:
                        model_type = st.selectbox(
                            f"Select Forecasting Model for {name}:",
                            ["Linear Regression", "Random Forest Regressor", "ARIMA Time Series", "LSTM Deep Learning"],
                            key=f"model_type_{index}"
                        )
                    with f_col2:
                        forecast_horizon = st.slider(
                            "Forecast Horizon (Future Days)", 
                            min_value=3, 
                            max_value=60, 
                            value=14, 
                            key=f"horizon_{index}"
                        )

                    # Split train/test
                    test_ratio = 0.2
                    split_idx = int(len(dataset) * (1 - test_ratio))
                    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
                    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

                    model = None
                    y_pred = None
                    future_predictions = None

                    # Execution of Selected Model
                    if model_type == "Linear Regression":
                        lr = LinearRegression()
                        lr.fit(X_train, y_train)
                        y_pred = lr.predict(X_test)
                        
                        future_days = np.array([((int(X['DayOfYear'].max()) + i) % 365) + 1 for i in range(1, forecast_horizon + 1)]).reshape(-1, 1)
                        future_predictions = lr.predict(pd.DataFrame(future_days, columns=['DayOfYear']))
                        st.info("Linear Regression establishes baseline demand trajectory based on seasonal ordinal day variance.")

                    elif model_type == "Random Forest Regressor":
                        rf = RandomForestRegressor(n_estimators=100, random_state=42)
                        rf.fit(X_train, y_train)
                        y_pred = rf.predict(X_test)

                        future_days = np.array([((int(X['DayOfYear'].max()) + i) % 365) + 1 for i in range(1, forecast_horizon + 1)]).reshape(-1, 1)
                        future_predictions = rf.predict(pd.DataFrame(future_days, columns=['DayOfYear']))
                        st.info("Random Forest Regressor captures non-linear shocks, peaks, and seasonal volatility.")

                    elif model_type == "ARIMA Time Series":
                        try:
                            arima = ARIMA(y_train.values, order=(2, 1, 1))
                            arima_fit = arima.fit()
                            y_pred = arima_fit.forecast(steps=len(y_test))
                            future_predictions = arima_fit.forecast(steps=forecast_horizon)
                            st.info("ARIMA models autoregressive and moving average trends in sequential demand observations.")
                        except Exception as e:
                            st.warning(f"ARIMA fallback: {e}")
                            y_pred = np.full(len(y_test), y_train.mean())
                            future_predictions = np.full(forecast_horizon, y_train.mean())

                    elif model_type == "LSTM Deep Learning":
                        scaler = MinMaxScaler(feature_range=(0, 1))
                        scaled_series = scaler.fit_transform(dataset[['Sales']].values)
                        time_steps = min(7, len(scaled_series) // 4) if len(scaled_series) >= 12 else 2

                        if len(scaled_series) > time_steps + 5:
                            X_lstm, y_lstm = [], []
                            for i in range(len(scaled_series) - time_steps):
                                X_lstm.append(scaled_series[i:i + time_steps, 0])
                                y_lstm.append(scaled_series[i + time_steps, 0])
                            X_lstm, y_lstm = np.array(X_lstm), np.array(y_lstm)
                            X_lstm = X_lstm.reshape((X_lstm.shape[0], X_lstm.shape[1], 1))

                            split_lstm = int(len(X_lstm) * 0.8)
                            X_tr_l, X_te_l = X_lstm[:split_lstm], X_lstm[split_lstm:]
                            y_tr_l, y_te_l = y_lstm[:split_lstm], y_lstm[split_lstm:]

                            lstm_model = Sequential([
                                LSTM(16, input_shape=(time_steps, 1), return_sequences=False),
                                Dense(1)
                            ])
                            lstm_model.compile(optimizer='adam', loss='mean_squared_error')
                            lstm_model.fit(X_tr_l, y_tr_l, epochs=6, batch_size=16, verbose=0)
                            
                            pred_scaled = lstm_model.predict(X_te_l, verbose=0)
                            y_pred = scaler.inverse_transform(pred_scaled).flatten()
                            y_test = scaler.inverse_transform(y_te_l.reshape(-1, 1)).flatten()

                            # Future rolling projection
                            curr_seq = scaled_series[-time_steps:].reshape(1, time_steps, 1)
                            fut_preds = []
                            for _ in range(forecast_horizon):
                                nxt = lstm_model.predict(curr_seq, verbose=0)[0, 0]
                                fut_preds.append(nxt)
                                curr_seq = np.roll(curr_seq, -1, axis=1)
                                curr_seq[0, -1, 0] = nxt
                            future_predictions = scaler.inverse_transform(np.array(fut_preds).reshape(-1, 1)).flatten()
                            st.info("LSTM neural network identifies sequential long-term dependencies across historical cycles.")
                        else:
                            st.warning("Not enough consecutive observations for multi-step LSTM training; fallback to moving average.")
                            y_pred = np.full(len(y_test), y.mean())
                            future_predictions = np.full(forecast_horizon, y.mean())

                    # Metrics & Visualizations
                    if y_pred is not None and len(y_test) > 0:
                        y_test_arr = np.array(y_test)
                        y_pred_arr = np.array(y_pred)
                        min_len = min(len(y_test_arr), len(y_pred_arr))
                        y_test_arr = y_test_arr[:min_len]
                        y_pred_arr = y_pred_arr[:min_len]

                        mae = mean_absolute_error(y_test_arr, y_pred_arr)
                        rmse = np.sqrt(mean_squared_error(y_test_arr, y_pred_arr))

                        m1, m2 = st.columns(2)
                        with m1:
                            st.metric("Mean Absolute Error (MAE)", f"{mae:.2f}")
                        with m2:
                            st.metric("Root Mean Squared Error (RMSE)", f"{rmse:.2f}")

                        # Actual vs Predicted Plot
                        fig_scatter = go.Figure()
                        fig_scatter.add_trace(go.Scatter(
                            x=y_test_arr, 
                            y=y_pred_arr, 
                            mode='markers', 
                            name='Predictions',
                            marker=dict(color='#2563EB', size=8, opacity=0.7)
                        ))
                        # Ideal line
                        min_val = min(y_test_arr.min(), y_pred_arr.min())
                        max_val = max(y_test_arr.max(), y_pred_arr.max())
                        fig_scatter.add_trace(go.Scatter(
                            x=[min_val, max_val], 
                            y=[min_val, max_val], 
                            mode='lines', 
                            name='Ideal 1:1 Fit',
                            line=dict(color='#EF4444', dash='dash')
                        ))
                        fig_scatter.update_layout(
                            title="Actual vs Predicted Demand Validation",
                            xaxis_title="Observed Demand",
                            yaxis_title="Model Predicted Demand",
                            template="plotly_white",
                            height=380
                        )
                        st.plotly_chart(fig_scatter, use_container_width=True)

                    # Future Forecast Table and Plot
                    if future_predictions is not None:
                        last_date = dataset[date_col].max()
                        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=forecast_horizon, freq='D')
                        future_df = pd.DataFrame({
                            'Date': future_dates,
                            'Projected Demand': np.maximum(0, np.array(future_predictions).flatten().round(2))
                        })

                        st.write("##### Future Demand Projections")
                        fig_future = go.Figure()
                        # Historical trace
                        hist_sample = dataset.tail(40)
                        fig_future.add_trace(go.Scatter(
                            x=hist_sample[date_col],
                            y=hist_sample['Sales'],
                            mode='lines+markers',
                            name='Historical Demand',
                            line=dict(color='#64748B')
                        ))
                        # Forecast trace
                        fig_future.add_trace(go.Scatter(
                            x=future_df['Date'],
                            y=future_df['Projected Demand'],
                            mode='lines+markers',
                            name='Forecasted Trajectory',
                            line=dict(color='#2563EB', width=3)
                        ))
                        fig_future.update_layout(
                            title=f"Demand Trajectory: Next {forecast_horizon} Days ({model_type})",
                            xaxis_title="Timeline",
                            yaxis_title="Demand (Units)",
                            template="plotly_white",
                            height=400
                        )
                        st.plotly_chart(fig_future, use_container_width=True)

                        c_down1, c_down2 = st.columns([1, 1])
                        with c_down1:
                            st.dataframe(future_df, use_container_width=True, height=200)
                        with c_down2:
                            st.download_button(
                                label="Download Forecast Projections (CSV)",
                                data=future_df.to_csv(index=False),
                                file_name=f"demand_forecast_{name}.csv",
                                mime="text/csv",
                                key=f"dl_{index}"
                            )
                else:
                    st.error("No valid numeric sales column could be processed for this dataset.")
    else:
        st.info("Upload a sales or inventory dataset (CSV/XLSX) above or choose a sample dataset to begin forecasting.")

def show_about():
    st.markdown("""
        <div class="hero-container">
            <span class="hero-badge">Architecture & Methodology</span>
            <h1 class="hero-title">About the Machine Learning Framework</h1>
            <p class="hero-subtitle">Algorithmic foundations for enterprise demand forecasting and inventory optimization.</p>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("1. Forecasting Model Methodologies")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
            ##### Linear Regression
            - Establishes parametric relationships between calendar cycles and historical order volumes.
            - Fast, interpretable, and effective for products with stable, linear consumption.
            
            ##### Random Forest Regressor
            - An ensemble non-parametric decision tree framework.
            - Aggregates decision trees across bootstrapping samples to capture non-linear demand shocks and seasonal promotions.
        """)
    with c2:
        st.markdown("""
            ##### ARIMA (Autoregressive Integrated Moving Average)
            - Statistical time-series framework accounting for autoregression, differencing for stationarity, and moving averages.
            - Well-suited for cyclical, non-stationary business cycles.
            
            ##### LSTM (Long Short-Term Memory Neural Networks)
            - Recurrent neural network architecture with memory cells to mitigate vanishing gradients.
            - Captures multi-period sequential dependencies and complex lag dynamics.
        """)

    st.markdown("---")
    st.subheader("2. Stock Control & Inventory Formulas")
    st.markdown("""
        The platform implements standard supply chain operations research formulations:
        - **Lead Time Demand ($LTD$):**  
          $$\\text{LTD} = \\bar{D} \\times L$$  
          *(where $\\bar{D}$ is Average Daily Demand and $L$ is Supplier Lead Time in days)*
        
        - **Safety Stock ($SS$):**  
          $$SS = Z \\times \\sigma_D \\times \\sqrt{L}$$  
          *(where $Z = 1.65$ corresponds to a 95% service level factor and $\\sigma_D$ is standard deviation of daily demand)*
        
        - **Reorder Point ($ROP$):**  
          $$ROP = LTD + SS = (\\bar{D} \\times L) + SS$$
    """)

    st.markdown("---")
    st.subheader("3. Authorship & Project Attribution")
    st.markdown("""
        - **Lead Developer & Maintainer:** Ranga
        - **Framework Version:** 2.0.0
        - **License:** MIT Open Source License
    """)

def show_ask_question():
    st.title("Framework Support & Inquiries")
    st.write("Submit inquiries or technical questions regarding forecasting models and inventory configurations.")

    with st.form("question_form"):
        category = st.selectbox(
            "Inquiry Category", 
            ["General Inquiry", "Demand Forecasting Models", "Inventory & Stock Control", "User Management", "Technical Support"]
        )
        question_text = st.text_area("Your Question / Issue Details:")
        user_email = st.text_input("Contact Email (optional):", value=st.session_state.get("user_email") or "")
        submitted = st.form_submit_button("Submit Question")

        if submitted:
            if question_text.strip():
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO questions (category, question, email) VALUES (?, ?, ?)",
                    (category, question_text.strip(), user_email.strip())
                )
                conn.commit()
                conn.close()
                st.success("Your inquiry has been logged successfully. Our team will review it.")
            else:
                st.error("Please enter a question before submitting.")

    st.markdown("---")
    st.subheader("Frequently Asked Questions")
    with st.expander("Which forecasting model is best for volatile consumer goods?"):
        st.write("Random Forest and LSTM models typically outperform linear models for volatile demand patterns due to their capacity to capture non-linear interactions.")
    with st.expander("How does the framework calculate the safety stock level?"):
        st.write("Safety stock is computed using the standard statistical model: $SS = Z \\times \\sigma_D \\times \\sqrt{L}$, protecting against standard demand variations over the supplier lead time.")
    with st.expander("Can I upload Excel (.xlsx) files as well as CSV?"):
        st.write("Yes, both CSV and XLSX formats are natively supported up to 5 concurrent datasets.")

    # Historical Inquiries
    if st.session_state.get("logged_in"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT category, question, created_at FROM questions ORDER BY id DESC LIMIT 5")
        recent_questions = cur.fetchall()
        conn.close()

        if recent_questions:
            st.markdown("---")
            st.subheader("Recent System Inquiries")
            for cat, q, created_at in recent_questions:
                st.markdown(f"- **[{cat}]** *\"{q}\"* ({created_at})")

def show_feedback():
    st.title("User Experience Feedback")
    st.write("Help us continuously enhance this Machine Learning Framework.")

    if 'rating' not in st.session_state:
        st.session_state.rating = 5

    st.write("**Overall Satisfaction Rating:**")
    star_cols = st.columns(5)
    for idx, col in enumerate(star_cols, start=1):
        with col:
            if st.button(f"{'⭐' * idx}", key=f"star_btn_{idx}", use_container_width=True):
                st.session_state.rating = idx

    st.info(f"Selected Rating: {'⭐' * st.session_state.rating} ({st.session_state.rating}/5 stars)")

    feedback_comments = st.text_area("Additional Feedback or Feature Requests:")
    if st.button("Submit Feedback", type="primary"):
        if feedback_comments.strip() or st.session_state.rating:
            st.success(f"Thank you for your rating of {st.session_state.rating} stars! Your feedback helps refine future iterations.")
        else:
            st.error("Please provide a rating or brief comment.")

def logout():
    st.title("Session Logout")
    st.write("Thank you for utilizing **A Machine Learning Framework for Demand Forecasting and Stock Control**.")

    if st.button("Confirm Logout", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Session closed successfully.")
        time.sleep(1)
        st.rerun()

# Application Controller & Routing
def main():
    if not st.session_state.logged_in:
        if st.session_state.current_page == "signup":
            signup_page()
        elif st.session_state.current_page == "reset":
            reset_password_page()  
        else:
            login_page()
    else:
        st.sidebar.markdown(f"""
            <div class="user-badge">
                <small style="color: #64748B; font-weight: 600;">ACTIVE SESSION</small><br>
                <strong style="color: #1E3A8A; font-size: 1.05rem;">👤 {st.session_state.username}</strong>
            </div>
        """, unsafe_allow_html=True)
        
        page = st.sidebar.radio(
            "Navigation Menu", 
            ["Framework Dashboard", "Methodology & Architecture", "Inquiries & Support", "Feedback", "Logout"]
        )

        if page == "Framework Dashboard":
            app()
        elif page == "Methodology & Architecture":
            show_about()
        elif page == "Inquiries & Support":
            show_ask_question()
        elif page == "Feedback":
            show_feedback()
        elif page == "Logout":
            logout()

if __name__ == "__main__":
    main()
