-- RoadSoS Database Initialization
-- Enables PostGIS extensions

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE roadsos_db TO roadsos;
