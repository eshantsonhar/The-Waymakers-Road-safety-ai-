#!/usr/bin/env python3
"""
RoadSoS Database Seed Script
Populates the database with realistic Bangalore-focused demo data.
"""
import sys
import os
import random
import uuid
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://roadsos:roadsos_secret@localhost:5432/roadsos_db"
)

print(f"Connecting to: {DATABASE_URL.split('@')[-1]}")

try:
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Test connection
    session.execute(text("SELECT 1"))
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print("Running in offline mode - seed data will be generated in memory")
    sys.exit(0)

# ============================================================
# Bangalore Hospital Data (50 hospitals)
# ============================================================
BANGALORE_HOSPITALS = [
    # Level 1 Trauma Centers
    ("Manipal Hospital Whitefield", "Manipal WF", 12.9698, 77.7499, "Whitefield Main Road, Bangalore", "Mahadevapura", 1, True, 40, 18, 80, 35),
    ("Apollo Hospital Bannerghatta", "Apollo BG", 12.8900, 77.5970, "Bannerghatta Road, Bangalore", "Bommanahalli", 1, True, 50, 22, 100, 45),
    ("Fortis Hospital Cunningham Road", "Fortis CR", 12.9900, 77.5900, "Cunningham Road, Bangalore", "Shivajinagar", 1, True, 35, 15, 70, 30),
    ("Narayana Health City", "Narayana HC", 12.8399, 77.6770, "Hosur Road, Bangalore", "Bommanahalli", 1, True, 80, 35, 150, 70),
    ("St. John's Medical College Hospital", "St. Johns", 12.9352, 77.6245, "Sarjapur Road, Bangalore", "Bommanahalli", 1, True, 45, 20, 90, 40),
    ("Sakra World Hospital", "Sakra", 12.9591, 77.6974, "Marathahalli, Bangalore", "Mahadevapura", 2, True, 30, 12, 60, 25),
    ("BGS Gleneagles Global Hospital", "BGS Global", 12.9100, 77.4900, "Kengeri, Bangalore", "Rajarajeshwari Nagar", 2, True, 25, 10, 50, 22),
    ("Aster CMI Hospital", "Aster CMI", 13.0358, 77.5970, "Hebbal, Bangalore", "Yelahanka", 2, True, 35, 14, 70, 30),
    ("Columbia Asia Hospital Whitefield", "Columbia WF", 12.9698, 77.7499, "Whitefield, Bangalore", "Mahadevapura", 3, False, 20, 8, 40, 18),
    ("Victoria Hospital", "Victoria", 12.9716, 77.5946, "Fort Road, Bangalore", "Shivajinagar", 2, True, 60, 25, 120, 55),
    # Level 2-3 Hospitals
    ("Sparsh Hospital", "Sparsh", 12.9800, 77.5800, "Infantry Road, Bangalore", "Shivajinagar", 2, True, 28, 11, 55, 24),
    ("Cloudnine Hospital Jayanagar", "Cloudnine JN", 12.9300, 77.5800, "Jayanagar, Bangalore", "Bommanahalli", 3, False, 15, 6, 30, 13),
    ("Motherhood Hospital Indiranagar", "Motherhood IN", 12.9784, 77.6408, "Indiranagar, Bangalore", "Mahadevapura", 3, False, 12, 5, 25, 11),
    ("Manipal Hospital Old Airport Road", "Manipal OAR", 12.9600, 77.6500, "Old Airport Road, Bangalore", "Mahadevapura", 2, True, 32, 13, 65, 28),
    ("Hosmat Hospital", "Hosmat", 12.9700, 77.5700, "Richmond Road, Bangalore", "Shivajinagar", 3, False, 18, 7, 35, 15),
    ("Sagar Hospital Jayanagar", "Sagar JN", 12.9250, 77.5900, "Jayanagar, Bangalore", "Bommanahalli", 3, False, 20, 8, 40, 17),
    ("Vikram Hospital", "Vikram", 12.9800, 77.5900, "Millers Road, Bangalore", "Shivajinagar", 2, True, 22, 9, 45, 20),
    ("Ramaiah Memorial Hospital", "Ramaiah", 13.0100, 77.5600, "MSR Nagar, Bangalore", "Dasarahalli", 2, True, 38, 16, 75, 33),
    ("Kempegowda Institute of Medical Sciences", "KIMS", 12.9400, 77.5500, "Banashankari, Bangalore", "Bommanahalli", 2, True, 42, 18, 85, 38),
    ("Bowring and Lady Curzon Hospital", "Bowring", 12.9800, 77.6100, "Shivajinagar, Bangalore", "Shivajinagar", 2, True, 55, 22, 110, 50),
]

# Generate additional 30 hospitals
ADDITIONAL_HOSPITALS = []
areas = [
    ("Electronic City", 12.8399, 77.6770, "Bommanahalli"),
    ("Koramangala", 12.9352, 77.6245, "Bommanahalli"),
    ("HSR Layout", 12.9116, 77.6389, "Bommanahalli"),
    ("BTM Layout", 12.9165, 77.6101, "Bommanahalli"),
    ("JP Nagar", 12.9063, 77.5857, "Bommanahalli"),
    ("Rajajinagar", 12.9900, 77.5500, "Dasarahalli"),
    ("Malleshwaram", 13.0035, 77.5700, "Dasarahalli"),
    ("Yelahanka", 13.1007, 77.5963, "Yelahanka"),
    ("Devanahalli", 13.2500, 77.7100, "Yelahanka"),
    ("Sarjapur", 12.8600, 77.7800, "Mahadevapura"),
]

for i, (area, lat, lon, district) in enumerate(areas):
    for j in range(3):
        ADDITIONAL_HOSPITALS.append((
            f"{area} Medical Center {j+1}",
            f"{area[:6]}-{j+1}",
            lat + random.uniform(-0.01, 0.01),
            lon + random.uniform(-0.01, 0.01),
            f"{area}, Bangalore",
            district,
            random.choice([2, 3, 4]),
            random.random() < 0.3,
            random.randint(10, 30),
            random.randint(3, 12),
            random.randint(20, 60),
            random.randint(8, 25),
        ))

ALL_HOSPITALS = BANGALORE_HOSPITALS + ADDITIONAL_HOSPITALS[:30]

BLOOD_TYPES = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
SPECIALISTS = ["Trauma Surgeon", "Orthopedic", "Neurosurgeon", "Cardiologist", "General Surgeon", "Anesthesiologist"]

def seed_hospitals():
    print("Seeding hospitals...")
    count = 0
    for hosp_data in ALL_HOSPITALS:
        (name, short_name, lat, lon, address, district,
         trauma_level, has_trauma, total_icu, avail_icu, total_emg, avail_emg) = hosp_data

        blood_types = random.sample(BLOOD_TYPES, random.randint(4, 8))
        specialists = random.sample(SPECIALISTS, random.randint(2, 5))

        session.execute(text("""
            INSERT INTO hospitals (
                id, name, short_name, location, latitude, longitude, address, district,
                phone, trauma_level, has_trauma_center, has_icu, has_cath_lab, has_neurosurgery,
                total_icu_beds, available_icu_beds, total_emergency_beds, available_emergency_beds,
                current_patient_load, max_patient_load, available_blood_types, active_specialists,
                suitability_score, load_percentage, is_active, is_on_alert, accepts_trauma
            ) VALUES (
                :id, :name, :short_name, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                :lat, :lon, :address, :district,
                :phone, :trauma_level, :has_trauma, true, :has_cath, :has_neuro,
                :total_icu, :avail_icu, :total_emg, :avail_emg,
                :load, :max_load, :blood_types::jsonb, :specialists::jsonb,
                :score, :load_pct, true, :on_alert, true
            ) ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid.uuid4()),
            "name": name,
            "short_name": short_name,
            "lat": lat,
            "lon": lon,
            "address": address,
            "district": district,
            "phone": f"080-{random.randint(10000000, 99999999)}",
            "trauma_level": trauma_level,
            "has_trauma": has_trauma,
            "has_cath": trauma_level == 1,
            "has_neuro": trauma_level <= 2,
            "total_icu": total_icu,
            "avail_icu": avail_icu,
            "total_emg": total_emg,
            "avail_emg": avail_emg,
            "load": random.randint(20, 70),
            "max_load": 100,
            "blood_types": str(blood_types).replace("'", '"'),
            "specialists": str(specialists).replace("'", '"'),
            "score": round(random.uniform(60, 95), 1),
            "load_pct": round(random.uniform(30, 80), 1),
            "on_alert": random.random() < 0.2,
        })
        count += 1

    session.commit()
    print(f"  ✅ Seeded {count} hospitals")


def seed_ambulances():
    print("Seeding ambulances...")
    base_stations = [
        ("Silk Board Station", 12.9177, 77.6228),
        ("Marathahalli Station", 12.9591, 77.6974),
        ("Hebbal Station", 13.0358, 77.5970),
        ("Koramangala Station", 12.9352, 77.6245),
        ("Yeshwanthpur Station", 13.0280, 77.5540),
        ("Electronic City Station", 12.8399, 77.6770),
        ("Whitefield Station", 12.9698, 77.7499),
        ("Kengeri Station", 12.9100, 77.4900),
        ("Yelahanka Station", 13.1007, 77.5963),
        ("Rajajinagar Station", 12.9900, 77.5500),
    ]

    count = 0
    for station_name, base_lat, base_lon in base_stations:
        for j in range(3):
            amb_lat = base_lat + random.uniform(-0.01, 0.01)
            amb_lon = base_lon + random.uniform(-0.01, 0.01)
            amb_type = random.choice(["BLS", "ALS", "MICU", "BLS", "ALS"])

            session.execute(text("""
                INSERT INTO ambulances (
                    id, vehicle_number, call_sign, ambulance_type,
                    location, latitude, longitude, heading, speed_kmh,
                    status, is_active, crew_count, has_paramedic, has_doctor,
                    base_station_name, base_latitude, base_longitude,
                    equipment, route_progress
                ) VALUES (
                    :id, :vnum, :callsign, :atype,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :lat, :lon, :heading, 0,
                    'AVAILABLE', true, 2, true, :has_doc,
                    :station, :blat, :blon,
                    '["Defibrillator", "Oxygen", "First Aid Kit", "Stretcher"]'::jsonb, 0
                ) ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid.uuid4()),
                "vnum": f"KA-01-{random.randint(1000, 9999)}",
                "callsign": f"AMB-{count+1:03d}",
                "atype": amb_type,
                "lat": amb_lat,
                "lon": amb_lon,
                "heading": random.uniform(0, 360),
                "has_doc": random.random() < 0.3,
                "station": station_name,
                "blat": base_lat,
                "blon": base_lon,
            })
            count += 1

    session.commit()
    print(f"  ✅ Seeded {count} ambulances")


def seed_users():
    print("Seeding demo users...")
    demo_users = [
        ("Arjun Sharma", "+91 98765 43210", "arjun@example.com", "DEMO_DEVICE_001", "O+"),
        ("Priya Patel", "+91 87654 32109", "priya@example.com", "DEMO_DEVICE_002", "A+"),
        ("Rahul Kumar", "+91 76543 21098", "rahul@example.com", "DEMO_DEVICE_003", "B+"),
    ]

    for name, phone, email, device_id, blood_type in demo_users:
        user_id = str(uuid.uuid4())
        session.execute(text("""
            INSERT INTO users (id, name, phone, email, device_id, blood_type, is_active, is_demo)
            VALUES (:id, :name, :phone, :email, :device_id, :blood_type, true, true)
            ON CONFLICT DO NOTHING
        """), {"id": user_id, "name": name, "phone": phone, "email": email,
               "device_id": device_id, "blood_type": blood_type})

        # Add emergency contacts
        contacts = [
            (f"{name.split()[0]}'s Spouse", f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}", "Spouse"),
            (f"{name.split()[0]}'s Parent", f"+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}", "Parent"),
        ]
        for cname, cphone, relation in contacts:
            session.execute(text("""
                INSERT INTO emergency_contacts (id, user_id, name, phone, relationship, priority, is_active)
                VALUES (:id, :uid, :name, :phone, :rel, 1, true)
                ON CONFLICT DO NOTHING
            """), {"id": str(uuid.uuid4()), "uid": user_id, "name": cname, "phone": cphone, "rel": relation})

    session.commit()
    print("  ✅ Seeded 3 demo users with emergency contacts")


def seed_road_segments():
    print("Seeding road segments...")
    hotspots = [
        ("Silk Board Junction", 12.9177, 77.6228, 12.9200, 77.6250, "Bommanahalli", "arterial"),
        ("Marathahalli Bridge", 12.9591, 77.6974, 12.9610, 77.7000, "Mahadevapura", "arterial"),
        ("KR Puram Bridge", 13.0050, 77.6960, 13.0070, 77.6990, "Mahadevapura", "highway"),
        ("Hebbal Flyover", 13.0358, 77.5970, 13.0380, 77.5990, "Yelahanka", "highway"),
        ("Tin Factory Junction", 12.9985, 77.6608, 13.0005, 77.6630, "Mahadevapura", "arterial"),
        ("Bannerghatta Road", 12.8900, 77.5970, 12.8920, 77.5990, "Bommanahalli", "arterial"),
        ("Outer Ring Road Bellandur", 12.9304, 77.6784, 12.9324, 77.6810, "Mahadevapura", "highway"),
        ("Hosur Road Electronic City", 12.8399, 77.6770, 12.8420, 77.6790, "Bommanahalli", "highway"),
        ("Tumkur Road Yeshwanthpur", 13.0280, 77.5540, 13.0300, 77.5560, "Dasarahalli", "highway"),
        ("Old Madras Road", 12.9900, 77.6500, 12.9920, 77.6520, "Mahadevapura", "arterial"),
    ]

    count = 0
    for name, slat, slon, elat, elon, district, road_type in hotspots:
        for j in range(20):  # 20 segments per hotspot = 200 total
            seg_slat = slat + random.uniform(-0.02, 0.02)
            seg_slon = slon + random.uniform(-0.02, 0.02)
            seg_elat = seg_slat + random.uniform(0.002, 0.008)
            seg_elon = seg_slon + random.uniform(0.002, 0.008)

            accident_freq = random.uniform(1, 18)
            surface = random.uniform(0.3, 0.9)
            curvature = random.uniform(0.05, 0.6)
            pothole_density = random.uniform(0.5, 8.0)
            risk_score = min(100, accident_freq * 3 + (1 - surface) * 20 + curvature * 15 + pothole_density * 3 + random.uniform(-10, 10))

            session.execute(text("""
                INSERT INTO road_segments (
                    id, name, road_type, district,
                    geometry, start_latitude, start_longitude, end_latitude, end_longitude,
                    length_km, speed_limit_kmh, surface_condition, curvature_index, pothole_density,
                    risk_score, accident_frequency_per_year, is_blackspot, prediction_confidence,
                    total_accidents, fatal_accidents, risk_factors
                ) VALUES (
                    :id, :name, :road_type, :district,
                    ST_SetSRID(ST_MakeLine(ST_MakePoint(:slon, :slat), ST_MakePoint(:elon, :elat)), 4326),
                    :slat, :slon, :elat, :elon,
                    :length, :speed, :surface, :curvature, :pothole,
                    :risk, :freq, :blackspot, :confidence,
                    :total_acc, :fatal_acc, :factors::jsonb
                ) ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid.uuid4()),
                "name": f"{name} - Seg {j+1}",
                "road_type": road_type,
                "district": district,
                "slat": seg_slat, "slon": seg_slon,
                "elat": seg_elat, "elon": seg_elon,
                "length": round(random.uniform(0.3, 1.5), 2),
                "speed": 60 if road_type == "arterial" else 80,
                "surface": round(surface, 2),
                "curvature": round(curvature, 2),
                "pothole": round(pothole_density, 1),
                "risk": round(risk_score, 1),
                "freq": round(accident_freq, 1),
                "blackspot": risk_score >= 70,
                "confidence": round(random.uniform(0.6, 0.95), 3),
                "total_acc": random.randint(5, 50),
                "fatal_acc": random.randint(0, 5),
                "factors": '{"accident_frequency": ' + str(round(accident_freq/20, 3)) + ', "surface_condition": ' + str(round(1-surface, 3)) + '}',
            })
            count += 1

    session.commit()
    print(f"  ✅ Seeded {count} road segments")


def seed_historical_accidents():
    print("Seeding historical accident events...")
    hotspot_locations = [
        (12.9177, 77.6228, "Bommanahalli"),
        (12.9591, 77.6974, "Mahadevapura"),
        (13.0050, 77.6960, "Mahadevapura"),
        (13.0358, 77.5970, "Yelahanka"),
        (12.9985, 77.6608, "Mahadevapura"),
        (12.8900, 77.5970, "Bommanahalli"),
        (12.9304, 77.6784, "Mahadevapura"),
        (12.8399, 77.6770, "Bommanahalli"),
        (13.0280, 77.5540, "Dasarahalli"),
        (12.9900, 77.6500, "Mahadevapura"),
    ]

    vehicle_types = ["Two-Wheeler", "Auto-Rickshaw", "Car", "SUV", "Bus", "Truck"]
    weather_conditions = ["Clear", "Cloudy", "Light Rain", "Heavy Rain", "Fog"]
    road_conditions = ["Dry", "Wet", "Potholed", "Under Construction"]
    time_of_day = ["morning", "afternoon", "evening", "night"]
    severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    count = 0
    for _ in range(500):
        hotspot = random.choice(hotspot_locations)
        lat = hotspot[0] + random.uniform(-0.01, 0.01)
        lon = hotspot[1] + random.uniform(-0.01, 0.01)
        district = hotspot[2]

        occurred_at = datetime.utcnow() - timedelta(
            days=random.randint(0, 365),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        session.execute(text("""
            INSERT INTO accident_events (
                id, location, latitude, longitude, district,
                event_type, severity, vehicle_type, vehicles_involved,
                casualties, fatalities, crash_probability_score, impact_force_g,
                speed_at_impact_kmh, weather_condition, road_condition, time_of_day,
                is_historical, is_demo, occurred_at
            ) VALUES (
                :id, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), :lat, :lon, :district,
                'crash', :severity, :vehicle, :vehicles,
                :casualties, :fatalities, :prob, :impact,
                :speed, :weather, :road, :tod,
                true, false, :occurred_at
            ) ON CONFLICT DO NOTHING
        """), {
            "id": str(uuid.uuid4()),
            "lat": lat, "lon": lon, "district": district,
            "severity": random.choice(severities),
            "vehicle": random.choice(vehicle_types),
            "vehicles": random.randint(1, 3),
            "casualties": random.randint(0, 4),
            "fatalities": random.randint(0, 2),
            "prob": round(random.uniform(0.75, 0.99), 3),
            "impact": round(random.uniform(2.0, 10.0), 2),
            "speed": round(random.uniform(20, 90), 1),
            "weather": random.choice(weather_conditions),
            "road": random.choice(road_conditions),
            "tod": random.choice(time_of_day),
            "occurred_at": occurred_at,
        })
        count += 1

    session.commit()
    print(f"  ✅ Seeded {count} historical accident events")


def main():
    print("\n🚨 RoadSoS Database Seeder")
    print("=" * 40)

    try:
        # Import models to create tables
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "database",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'app', 'database.py')
        )

        seed_hospitals()
        seed_ambulances()
        seed_users()
        seed_road_segments()
        seed_historical_accidents()

        print("\n✅ Database seeding complete!")
        print(f"   Hospitals: {len(ALL_HOSPITALS)}")
        print(f"   Ambulances: 30")
        print(f"   Road Segments: 200")
        print(f"   Historical Accidents: 500")

    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
