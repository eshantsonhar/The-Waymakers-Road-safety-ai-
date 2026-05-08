#!/usr/bin/env python3
"""
RoadSoS Demo Scenario Generator
Generates a sequence of simulated incidents for demonstration purposes.
"""
import asyncio
import httpx
import random
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

SCENARIOS = [
    {
        "name": "Rush Hour Multi-Crash",
        "description": "Simulates 3 simultaneous crashes during evening rush hour",
        "incidents": [
            {"lat": 12.9177, "lon": 77.6228, "severity": "HIGH", "location": "Silk Board Junction"},
            {"lat": 12.9591, "lon": 77.6974, "severity": "CRITICAL", "location": "Marathahalli Bridge"},
            {"lat": 13.0358, "lon": 77.5970, "severity": "MEDIUM", "location": "Hebbal Flyover"},
        ],
        "delay_between": 5,
    },
    {
        "name": "Highway Rollover",
        "description": "Critical rollover accident on Hosur Road",
        "incidents": [
            {"lat": 12.8399, "lon": 77.6770, "severity": "CRITICAL", "location": "Hosur Road Electronic City"},
        ],
        "delay_between": 0,
    },
    {
        "name": "Chain Collision",
        "description": "Multiple vehicle pile-up on Outer Ring Road",
        "incidents": [
            {"lat": 12.9304, "lon": 77.6784, "severity": "HIGH", "location": "Outer Ring Road Bellandur"},
            {"lat": 12.9310, "lon": 77.6790, "severity": "MEDIUM", "location": "Outer Ring Road Bellandur (Secondary)"},
        ],
        "delay_between": 10,
    },
]


async def run_scenario(scenario: dict):
    """Execute a demo scenario."""
    print(f"\n🎬 Running scenario: {scenario['name']}")
    print(f"   {scenario['description']}")

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        for i, incident_data in enumerate(scenario["incidents"]):
            print(f"\n   📍 Creating incident {i+1}/{len(scenario['incidents'])}: {incident_data['location']}")

            try:
                response = await client.post("/api/incidents/", json={
                    "latitude": incident_data["lat"],
                    "longitude": incident_data["lon"],
                    "severity": incident_data["severity"],
                    "crash_probability_score": random.uniform(0.80, 0.98),
                    "confidence_level": "HIGH",
                    "event_classification": "CRASH",
                    "is_manual_sos": False,
                })

                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Incident created: {data.get('incident_number', 'N/A')}")
                    print(f"      Severity: {incident_data['severity']}")
                    print(f"      Location: {incident_data['location']}")
                else:
                    print(f"   ⚠️  API returned {response.status_code}")

            except Exception as e:
                print(f"   ❌ Failed to create incident: {e}")

            if i < len(scenario["incidents"]) - 1:
                print(f"   ⏳ Waiting {scenario['delay_between']}s...")
                await asyncio.sleep(scenario["delay_between"])


async def run_sensor_simulation():
    """Simulate sensor data stream."""
    print("\n📡 Running sensor simulation...")

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        # Simulate normal driving
        print("   Normal driving phase...")
        for i in range(5):
            await client.post("/api/detection/analyze", json={
                "device_id": "DEMO_DEVICE_001",
                "accel_x": random.uniform(-0.5, 0.5),
                "accel_y": random.uniform(-0.3, 0.3),
                "accel_z": 9.81 + random.uniform(-0.2, 0.2),
                "gyro_x": random.uniform(-5, 5),
                "gyro_y": random.uniform(-5, 5),
                "gyro_z": random.uniform(-3, 3),
                "latitude": 12.9716,
                "longitude": 77.5946,
                "speed_kmh": random.uniform(40, 60),
                "sound_db": random.uniform(35, 55),
            })
            await asyncio.sleep(0.5)

        # Simulate crash
        print("   💥 Simulating crash event...")
        response = await client.post("/api/detection/simulate/SEVERE_CRASH")
        if response.status_code == 200:
            data = response.json()
            print(f"   Crash detected: {data.get('crash_detected', False)}")
            print(f"   Max probability: {data.get('max_probability', 0):.2%}")


async def main():
    print("🚨 RoadSoS Demo Scenario Generator")
    print("=" * 50)
    print(f"API: {API_BASE}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API health
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=5) as client:
            response = await client.get("/health")
            if response.status_code == 200:
                print("\n✅ API is healthy")
            else:
                print(f"\n⚠️  API returned {response.status_code}")
    except Exception as e:
        print(f"\n❌ Cannot connect to API: {e}")
        print("Make sure the backend is running: uvicorn app.main:app --reload")
        return

    print("\nAvailable scenarios:")
    for i, scenario in enumerate(SCENARIOS):
        print(f"  {i+1}. {scenario['name']} - {scenario['description']}")

    print("\nRunning all scenarios...")

    for scenario in SCENARIOS:
        await run_scenario(scenario)
        await asyncio.sleep(3)

    await run_sensor_simulation()

    print("\n✅ Demo scenarios complete!")
    print("Check the Command Center dashboard to see the incidents.")


if __name__ == "__main__":
    asyncio.run(main())
