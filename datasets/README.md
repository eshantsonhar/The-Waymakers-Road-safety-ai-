# RoadSoS Datasets

## Data Sources

### Indian Road Accident Data
- **MoRTH (Ministry of Road Transport & Highways)**: Annual road accident statistics
  - Source: https://morth.nic.in/road-accident-in-india
  - Used for: Historical accident frequency, severity distribution, vehicle type breakdown

- **NCRB (National Crime Records Bureau)**: Accidental deaths and injuries
  - Source: https://ncrb.gov.in/accidental-deaths-suicides-in-india
  - Used for: Fatality rates, time-of-day patterns, road type analysis

- **data.gov.in**: Open government data portal
  - Source: https://data.gov.in/catalog/road-accidents-india
  - Used for: State-wise accident data, district-level statistics

### Bangalore-Specific Data
- **BBMP (Bruhat Bengaluru Mahanagara Palike)**: Road infrastructure data
  - Used for: Road segment classification, pothole reports

- **BMTC/BMRCL**: Traffic density data
  - Used for: Peak hour traffic patterns

- **Karnataka State Police**: Accident hotspot data
  - Used for: Blackspot identification, accident cluster analysis

## Mock Data Description

### bangalore_hospitals.json
50 hospitals in Bangalore with:
- GPS coordinates (real locations)
- Trauma capability levels (1-4)
- ICU bed counts
- Specialist availability
- Blood type inventory

### bangalore_accident_hotspots.json
Top 15 accident-prone locations in Bangalore:
- Silk Board Junction (highest risk)
- Marathahalli Bridge
- KR Puram Bridge
- Hebbal Flyover
- Tin Factory Junction
- And 10 more...

### road_segments_bangalore.json
200 road segments with:
- GPS linestring geometry
- Road type (highway/arterial/collector/local)
- Surface condition scores
- Curvature index
- Pothole density
- Historical accident frequency

### historical_accidents_500.json
500 historical accident records (synthetic, based on real patterns):
- Location (GPS coordinates)
- Severity
- Vehicle type
- Weather conditions
- Time of day
- Impact force estimates

## Key Statistics (Based on MoRTH 2022 Data)

- India had **4,61,312** road accidents in 2022
- **1,68,491** fatalities (highest in the world)
- Karnataka: **11,131** accidents, **5,765** fatalities
- Bangalore Urban: ~2,800 accidents per year
- Peak accident hours: 6-9 PM (evening rush)
- Most dangerous vehicle: Two-wheelers (44% of fatalities)
- Most dangerous road type: National Highways (31% of accidents)

## Bangalore Accident Hotspot Analysis

Based on traffic police data and news reports:

| Rank | Location | Avg Accidents/Year | Primary Cause |
|------|----------|-------------------|---------------|
| 1 | Silk Board Junction | 47 | Traffic congestion, signal jumping |
| 2 | Marathahalli Bridge | 38 | Speeding, lane changing |
| 3 | KR Puram Bridge | 31 | Heavy vehicle movement |
| 4 | Hebbal Flyover | 28 | High speed, poor visibility |
| 5 | Tin Factory Junction | 24 | Signal violation |
| 6 | Bannerghatta Road | 22 | Pedestrian crossing |
| 7 | Outer Ring Road | 19 | Speeding, drunk driving |
| 8 | Hosur Road | 17 | Heavy traffic, potholes |

## License

Mock/synthetic data generated for demonstration purposes.
Real data sourced from publicly available government datasets.
Attribution required for any public use.
