
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

SQL_DIR = Path(__file__).parent / "sql"

USERS = [
    ("Arman Bekov",     "arman.bekov@gmail.com",   "1998-03-14", "+77011110001"),
    ("Zarina Seiit",    "zarina.seiit@mail.ru",    "2000-07-21", "+77011110002"),
    ("Daniyar Nurlan",  "daniyar.n@gmail.com",     "1995-11-02", "+77011110003"),
    ("Aigerim Sadykova","aigerim.s@kbtu.kz",       "2002-01-30", "+77011110004"),
    ("Timur Omarov",    "timur.omarov@gmail.com",  "1992-05-17", "+77011110005"),
    ("Madina Kenzhe",   "madina.k@yandex.kz",      "1999-09-09", "+77011110006"),
    ("Alikhan Dauren",  "alikhan.d@gmail.com",     "2001-12-25", "+77011110007"),
    ("Dana Rakhim",     "dana.rakhim@mail.ru",     "1997-04-04", "+77011110008"),
    ("Nursultan Ayan",  "nursultan.a@gmail.com",   "1994-08-19", "+77011110009"),
    ("Karina Bolat",    "karina.bolat@kbtu.kz",    "2003-02-11", "+77011110010"),
]

CARS = [  # plate, brand, model, year, price_per_hour, status
    ("777 AAA 02", "Toyota",    "Camry",    2021, 2500, "available"),
    ("123 BCD 02", "Hyundai",   "Elantra",  2022, 2000, "available"),
    ("456 KLM 02", "Kia",       "K5",       2023, 2600, "available"),
    ("789 XYZ 02", "Chevrolet", "Cobalt",   2020, 1500, "available"),
    ("321 QWE 02", "Tesla",     "Model 3",  2023, 4500, "available"),
    ("654 RTY 02", "BMW",       "320i",     2022, 4000, "available"),
    ("987 UIO 02", "Skoda",     "Octavia",  2021, 1900, "available"),
    ("159 PAS 02", "Lada",      "Vesta",    2019, 1200, "maintenance"),
]

RENTALS = [  # user_id, car_id, start_time, end_time, status   (price is set by a trigger)
    (1, 1, "2026-09-01 10:00", "2026-09-01 14:30", "completed"),
    (2, 2, "2026-09-02 09:00", "2026-09-02 11:00", "completed"),
    (3, 3, "2026-09-03 18:00", "2026-09-04 08:00", "completed"),
    (1, 2, "2026-09-05 12:00", "2026-09-05 15:15", "completed"),
    (4, 4, "2026-09-06 08:00", "2026-09-06 20:00", "completed"),
    (5, 1, "2026-09-10 10:00", "2026-09-10 12:00", "completed"),
    (2, 5, "2026-09-12 14:00", "2026-09-12 16:00", "completed"),
    (6, 6, "2026-09-15 09:00", "2026-09-15 19:00", "completed"),
    (3, 1, "2026-10-01 10:00", "2026-10-01 13:00", "completed"),
    (7, 3, "2026-10-20 10:00", None,                "active"),
    (8, 4, "2026-10-25 08:00", None,                "active"),
    (1, 7, "2026-11-05 10:00", "2026-11-05 18:00", "booked"),
    (5, 2, "2026-10-10 10:00", "2026-10-10 12:00", "cancelled"),
]


def run_sql_file(conn, name):
    conn.execute((SQL_DIR / name).read_text(encoding="utf-8"))
    print(f"  executed {name}")


def main():
    load_dotenv()
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        run_sql_file(conn, "01_schema.sql")
        run_sql_file(conn, "02_functions_triggers.sql")
        cur=conn.cursor()

        cur.executemany(
            "INSERT INTO users (user_name, email, date_of_birth, phone_number) VALUES (%s, %s, %s, %s)", USERS)
        cur.executemany(
            "INSERT INTO cars (plate_number, brand, model, year, price_per_hour, status) "
            "VALUES (%s, %s, %s, %s, %s, %s)", CARS)
        cur.executemany(
            "INSERT INTO rentals (user_id, car_id, start_time, end_time, status) VALUES (%s, %s, %s, %s, %s)",
            RENTALS)
        cur.execute("""
            INSERT INTO payments (rental_id, payment_date, amount, method)
            SELECT rental_id, end_time, price,
                   (ARRAY['card','cash','kaspi','transfer'])[1 + rental_id % 4]
            FROM rentals WHERE status = 'completed'
        """)
        print(f"  seeded {len(USERS)} users, {len(CARS)} cars, {len(RENTALS)} rentals + payments")

        run_sql_file(conn, "04_views_roles.sql")
        conn.commit()
    print("Database is ready.")


if __name__ == "__main__":
    main()
