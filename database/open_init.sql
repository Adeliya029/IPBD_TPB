-- Table untuk data cuaca real-time dari Open-Meteo
CREATE TABLE IF NOT EXISTS weather_realtime (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    province VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    temperature FLOAT,
    feels_like FLOAT,
    humidity FLOAT,
    precipitation FLOAT,
    weather_code INTEGER,
    weather_condition VARCHAR(100),
    cloud_cover FLOAT,
    pressure_msl FLOAT,
    surface_pressure FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    wind_gusts FLOAT,
    data_time TIMESTAMP,
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index untuk query yang sering digunakan
CREATE INDEX IF NOT EXISTS idx_weather_realtime_timestamp ON weather_realtime(timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_realtime_city ON weather_realtime(city);
CREATE INDEX IF NOT EXISTS idx_weather_realtime_province ON weather_realtime(province);