import sqlite3
from datetime import datetime

def get_connection():
    return sqlite3.connect("health.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Medications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        time TEXT NOT NULL
    )
    """)
    
    # Fitness Logs table (NEW)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fitness_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity TEXT NOT NULL,
        duration TEXT NOT NULL,
        date_logged TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# --- Medication Functions ---
def add_medicine(name, time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO medications (name, time) VALUES (?, ?)", (name, time))
    conn.commit()
    conn.close()

def get_all_medicines():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medications")
    meds = cursor.fetchall()
    conn.close()
    return meds

# --- Fitness Functions (NEW) ---
def add_fitness_log(activity, duration):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO fitness_logs (activity, duration) VALUES (?, ?)", (activity, duration))
    conn.commit()
    conn.close()

def get_recent_fitness_logs():
    conn = get_connection()
    cursor = conn.cursor()
    # Grabs the 5 most recent workouts and formats the date
    cursor.execute("SELECT activity, duration, date(date_logged) FROM fitness_logs ORDER BY id DESC LIMIT 5")
    logs = cursor.fetchall()
    conn.close()
    return logs

def get_fitness_data_for_chart():
    conn = get_connection()
    cursor = conn.cursor()
    

    cursor.execute("SELECT date(date_logged), COUNT(id) FROM fitness_logs GROUP BY date(date_logged)")
    data = cursor.fetchall()
    conn.close()
    return data

# Symptoms Table
def init_symptoms():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS symptoms (id INTEGER PRIMARY KEY, note TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def add_symptom(note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO symptoms (note) VALUES (?)", (note,))
    conn.commit()
    conn.close()


init_db()

init_symptoms()