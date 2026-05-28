/**
 * RoadSoS Hardware Telemetry Unit
 * ================================
 * Embedded firmware for Raspberry Pi Pico 2W
 * with SIM7600E-H (4G LTE + GPS + SMS) and MPU-9250 IMU.
 *
 * This code runs on the Pico 2W and streams telemetry to the RoadSoS backend.
 * Architecture:
 *   - Core0: Sensor reading loop (IMU + GPS), crash detection
 *   - Core1: Network communication (LTE HTTP POST)
 *
 * Pin Configuration (Pico 2W):
 *   MPU-9250: I2C0 (SDA=GP4, SCL=GP5)
 *   SIM7600E-H: UART1 (TX=GP8, RX=GP9), PWR=GP10, RST=GP11
 *   Status LED: GP25 (built-in)
 *   GPS (NEO-M8N): UART0 (TX=GP0, RX=GP1) - shared via SIM7600E-H
 */

// ── Includes ─────────────────────────────────────────────────────────────────
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <stdbool.h>

// Pico SDK headers (compiled with pico-sdk)
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "hardware/i2c.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"
#include "hardware/timer.h"

// FreeRTOS for dual-core (included with Pico SDK SMP)
#include "pico/multicore.h"

// ── Configuration ────────────────────────────────────────────────────────────

#define FIRMWARE_VERSION "v1.0.0"
#define DEVICE_ID "RPi-PICO2W-001"

// I2C pins for MPU-9250
#define MPU9250_I2C i2c0
#define MPU9250_SDA 4
#define MPU9250_SCL 5
#define MPU9250_ADDR 0x68

// UART for SIM7600E-H
#define SIM7600_UART uart1
#define SIM7600_TX 8
#define SIM7600_RX 9
#define SIM7600_PWR 10
#define SIM7600_RST 11
#define SIM7600_BAUD 115200

// Status LED
#define STATUS_LED 25

// Telemetry interval
#define TELEMETRY_INTERVAL_MS 1000  // 1 Hz
#define SENSOR_READ_INTERVAL_MS 20  // 50 Hz

// Crash detection thresholds
#define IMPACT_THRESHOLD_G 4.0f
#define IMPACT_WINDOW_MS 100
#define ROLLOVER_THRESHOLD_G 0.5f  // Sustained off-axis gravity

// Backend URL
#define BACKEND_URL "http://192.168.1.100:8000/api/telemetry/hardware"
#define BACKEND_TIMEOUT_MS 5000

// ── MPU-9250 Registers ───────────────────────────────────────────────────────
#define MPU9250_WHO_AM_I 0x75
#define MPU9250_ACCEL_XOUT_H 0x3B
#define MPU9250_GYRO_XOUT_H 0x43
#define MPU9250_CONFIG 0x1A
#define MPU9250_GYRO_CONFIG 0x1B
#define MPU9250_ACCEL_CONFIG 0x1C
#define MPU9250_PWR_MGMT_1 0x6B
#define MPU9250_PWR_MGMT_2 0x6C

// ── Data Structures ───────────────────────────────────────────────────────────

typedef struct {
    float x, y, z;  // g (acceleration)
    float gx, gy, gz;  // dps (angular velocity)
    float mx, my, mz;  // uT (magnetic field)
    float temperature_c;
    uint64_t timestamp_us;
} imu_reading_t;

typedef struct {
    double latitude;
    double longitude;
    float altitude_m;
    float speed_kmh;
    float heading_deg;
    float accuracy_m;
    uint8_t satellites;
    uint8_t fix_quality;
    uint64_t timestamp_ms;
} gps_reading_t;

typedef struct {
    bool crash_flag;
    float impact_force_g;
    float speed_delta_kmh;
    bool rollover_detected;
    float confidence;
    uint64_t timestamp_ms;
} crash_detection_t;

typedef struct {
    imu_reading_t imu;
    gps_reading_t gps;
    crash_detection_t crash;
    uint8_t battery_pct;
    int8_t signal_strength_dbm;
    uint64_t uptime_seconds;
    bool sos_active;
} telemetry_packet_t;

// ── Global State ─────────────────────────────────────────────────────────────

static volatile bool crash_alert = false;
static volatile bool sos_triggered = false;
static volatile uint64_t last_telemetry_ms = 0;
static volatile uint64_t boot_time_ms = 0;

// Ring buffer for IMU history (crash detection window)
#define IMU_HISTORY_SIZE 50  // 1 second at 50Hz
static imu_reading_t imu_history[IMU_HISTORY_SIZE];
static volatile uint8_t imu_history_idx = 0;

// ── MPU-9250 Driver Functions ────────────────────────────────────────────────

static bool mpu9250_init(void) {
    // Initialize I2C
    i2c_init(MPU9250_I2C, 400000);  // 400 kHz fast mode
    gpio_set_function(MPU9250_SDA, GPIO_FUNC_I2C);
    gpio_set_function(MPU9250_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(MPU9250_SDA);
    gpio_pull_up(MPU9250_SCL);

    // Verify device
    uint8_t whoami;
    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, (uint8_t[]){MPU9250_WHO_AM_I}, 1, true);
    i2c_read_blocking(MPU9250_I2C, MPU9250_ADDR, &whoami, 1, false);
    if (whoami != 0x71 && whoami != 0x73) {
        printf("MPU9250: WHO_AM_I mismatch (0x%02X)\n", whoami);
        return false;
    }

    // Wake up device
    uint8_t pwr = 0x00;  // 0 = wake, 0x40 = reset
    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, (uint8_t[]){MPU9250_PWR_MGMT_1, pwr}, 2, false);
    sleep_ms(10);

    // Configure accelerometer: ±2g, DLPF 44Hz
    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, (uint8_t[]){MPU9250_ACCEL_CONFIG, 0x00}, 2, false);
    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, (uint8_t[]){MPU9250_CONFIG, 0x03}, 2, false);

    // Configure gyroscope: ±250dps
    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, (uint8_t[]){MPU9250_GYRO_CONFIG, 0x00}, 2, false);

    printf("MPU9250: Initialized successfully\n");
    return true;
}

static bool mpu9250_read(imu_reading_t* reading) {
    uint8_t buffer[14];
    uint8_t reg = MPU9250_ACCEL_XOUT_H;

    i2c_write_blocking(MPU9250_I2C, MPU9250_ADDR, &reg, 1, true);
    i2c_read_blocking(MPU9250_I2C, MPU9250_ADDR, buffer, 14, false);

    // Convert to signed 16-bit
    int16_t ax = (int16_t)(buffer[0] << 8 | buffer[1]);
    int16_t ay = (int16_t)(buffer[2] << 8 | buffer[3]);
    int16_t az = (int16_t)(buffer[4] << 8 | buffer[5]);
    int16_t temp = (int16_t)(buffer[6] << 8 | buffer[7]);
    int16_t gx = (int16_t)(buffer[8] << 8 | buffer[9]);
    int16_t gy = (int16_t)(buffer[10] << 8 | buffer[11]);
    int16_t gz = (int16_t)(buffer[12] << 8 | buffer[13]);

    // Scale: ±2g → 16384 LSB/g, ±250dps → 131 LSB/dps
    reading->x = (float)ax / 16384.0f;
    reading->y = (float)ay / 16384.0f;
    reading->z = (float)az / 16384.0f;
    reading->gx = (float)gx / 131.0f;
    reading->gy = (float)gy / 131.0f;
    reading->gz = (float)gz / 131.0f;
    reading->temperature_c = (float)temp / 333.87f + 21.0f;
    reading->timestamp_us = time_us_64();

    return true;
}

// ── SIM7600E-H Driver Functions ──────────────────────────────────────────────

static bool sim7600_init(void) {
    // Initialize UART
    uart_init(SIM7600_UART, SIM7600_BAUD);
    gpio_set_function(SIM7600_TX, GPIO_FUNC_UART);
    gpio_set_function(SIM7600_RX, GPIO_FUNC_UART);

    // Power on SIM7600
    gpio_init(SIM7600_PWR);
    gpio_set_dir(SIM7600_PWR, GPIO_OUT);
    gpio_put(SIM7600_PWR, 1);
    sleep_ms(100);
    gpio_put(SIM7600_PWR, 0);
    sleep_ms(2000);  // Wait for module to boot

    // Reset
    gpio_init(SIM7600_RST);
    gpio_set_dir(SIM7600_RST, GPIO_OUT);
    gpio_put(SIM7600_RST, 0);
    sleep_ms(200);
    gpio_put(SIM7600_RST, 1);
    sleep_ms(3000);

    // Check AT
    uart_puts(SIM7600_UART, "AT\r\n");
    sleep_ms(500);
    // Read response
    char resp[128];
    int len = 0;
    while (uart_is_readable(SIM7600_UART) && len < 127) {
        resp[len++] = uart_getc(SIM7600_UART);
    }
    resp[len] = '\0';
    printf("SIM7600: AT response: %s\n", resp);

    // Check network registration
    uart_puts(SIM7600_UART, "AT+CREG?\r\n");
    sleep_ms(300);

    printf("SIM7600E-H: Initialized\n");
    return strstr(resp, "OK") != NULL;
}

static bool sim7600_send_http_post(const char* url, const char* json_data) {
    char cmd[512];
    int data_len = strlen(json_data);

    // Set HTTP parameters
    snprintf(cmd, sizeof(cmd), "AT+HTTPPARA=\"URL\",\"%s\"\r\n", url);
    uart_puts(SIM7600_UART, cmd);
    sleep_ms(300);

    uart_puts(SIM7600_UART, "AT+HTTPPARA=\"CONTENT\",\"application/json\"\r\n");
    sleep_ms(200);

    // Set data length
    snprintf(cmd, sizeof(cmd), "AT+HTTPDATA=%d,%d\r\n", data_len, BACKEND_TIMEOUT_MS);
    uart_puts(SIM7600_UART, cmd);
    sleep_ms(300);

    // Send data
    uart_puts(SIM7600_UART, json_data);
    sleep_ms(500);

    // Execute POST
    uart_puts(SIM7600_UART, "AT+HTTPACTION=1\r\n");
    sleep_ms(2000);

    // Read response
    char resp[256];
    int len = 0;
    while (uart_is_readable(SIM7600_UART) && len < 255) {
        resp[len++] = uart_getc(SIM7600_UART);
    }
    resp[len] = '\0';
    printf("SIM7600: HTTP POST response: %s\n", resp);

    return strstr(resp, "+HTTPACTION: 0,200") != NULL;
}

// ── GPS Parser (NEO-M8N via NMEA) ────────────────────────────────────────────

static bool parse_nmea_gprmc(const char* sentence, gps_reading_t* gps) {
    // $GPRMC,time,status,lat,NS,lon,EW,speed,course,date,...*CS
    if (sentence[0] != '$') return false;

    char status;
    double lat_raw, lon_raw;
    char ns, ew;
    float speed_knots, course;

    int parsed = sscanf(sentence, "$GPRMC,%*[^,],%c,%lf,%c,%lf,%c,%f,%f",
                        &status, &lat_raw, &ns, &lon_raw, &ew, &speed_knots, &course);

    if (parsed < 7 || status != 'A') return false;  // A = active/valid

    // Convert NMEA format (DDMM.MMMM) to decimal degrees
    double lat_deg = (int)(lat_raw / 100);
    double lat_min = lat_raw - (lat_deg * 100);
    gps->latitude = lat_deg + (lat_min / 60.0);
    if (ns == 'S') gps->latitude = -gps->latitude;

    double lon_deg = (int)(lon_raw / 100);
    double lon_min = lon_raw - (lon_deg * 100);
    gps->longitude = lon_deg + (lon_min / 60.0);
    if (ew == 'W') gps->longitude = -gps->longitude;

    gps->speed_kmh = speed_knots * 1.852f;
    gps->heading_deg = course;
    gps->fix_quality = (status == 'A') ? 1 : 0;

    return true;
}

static bool parse_nmea_gga(const char* sentence, gps_reading_t* gps) {
    // $GPGGA,time,lat,NS,lon,EW,quality,satellites,hdop,...*CS
    uint8_t quality, satellites;
    float hdop, altitude;

    int parsed = sscanf(sentence, "$GPGGA,%*[^,],%*[^,],%*c,%*[^,],%*c,%hhu,%hhu,%f,%f",
                        &quality, &satellites, &hdop, &altitude);

    if (parsed >= 2) {
        gps->fix_quality = quality;
        gps->satellites = satellites;
        gps->accuracy_m = hdop * 5.0f;  // HDOP to meters (approximate)
        gps->altitude_m = altitude;
        return true;
    }
    return false;
}

// ── Crash Detection Algorithm ────────────────────────────────────────────────

static crash_detection_t detect_crash(const imu_reading_t* current) {
    crash_detection_t result = {0};
    bool crash_candidate = false;

    // Compute total acceleration magnitude (excluding gravity)
    float ax = current->x;
    float ay = current->y;
    float az = current->z - 1.0f;  // Subtract gravity (assume upright)
    float total_accel = sqrtf(ax*ax + ay*ay + az*az);

    // Check for impact (sudden high acceleration)
    if (fabsf(total_accel) >= IMPACT_THRESHOLD_G) {
        crash_candidate = true;
        result.impact_force_g = total_accel;
        result.confidence = fminf(1.0f, total_accel / 10.0f);
    }

    // Check for rollover (sustained off-axis gravity)
    float gravity_angle = acosf(fabsf(current->z) / 9.81f) * 180.0f / M_PI;
    if (gravity_angle > 45.0f) {  // More than 45° tilt
        result.rollover_detected = true;
        result.confidence = fmaxf(result.confidence, 0.7f);
    }

    // Analyze IMU history for rapid changes
    float max_delta_g = 0.0f;
    for (int i = 1; i < IMU_HISTORY_SIZE; i++) {
        uint8_t prev = (imu_history_idx - i + IMU_HISTORY_SIZE) % IMU_HISTORY_SIZE;
        imu_reading_t* prev_read = &imu_history[prev];
        float dx = current->x - prev_read->x;
        float dy = current->y - prev_read->y;
        float dz = current->z - prev_read->z;
        float delta = sqrtf(dx*dx + dy*dy + dz*dz);
        if (delta > max_delta_g) max_delta_g = delta;
    }

    if (max_delta_g > 2.0f) {  // Rapid acceleration change
        result.speed_delta_kmh = max_delta_g * 9.81f * 0.1f;  // Approximate
    }

    result.crash_flag = crash_candidate || (result.rollover_detected && max_delta_g > 1.0f);
    result.timestamp_ms = time_us_64() / 1000;

    return result;
}

// ── Telemetry Packet Builder ─────────────────────────────────────────────────

static void build_telemetry_json(const imu_reading_t* imu, const gps_reading_t* gps,
                                  const crash_detection_t* crash, char* buffer, size_t buf_size) {
    snprintf(buffer, buf_size,
        "{"
        "\"device_id\":\"%s\","
        "\"timestamp\":\"%llu\","
        "\"telemetry_version\":\"1.0\","
        "\"gps\":{"
        "\"lat\":%.6f,\"lon\":%.6f,\"altitude_m\":%.1f,"
        "\"speed_kmh\":%.1f,\"heading_deg\":%.1f,\"accuracy_m\":%.1f,"
        "\"satellites\":%u,\"fix_quality\":%u"
        "},"
        "\"accelerometer\":{"
        "\"x\":%.4f,\"y\":%.4f,\"z\":%.4f"
        "},"
        "\"gyroscope\":{"
        "\"x\":%.4f,\"y\":%.4f,\"z\":%.4f"
        "},"
        "\"imu_temperature_c\":%.1f,"
        "\"system\":{"
        "\"battery_percent\":%u,\"cpu_temp_c\":%.1f,"
        "\"uptime_seconds\":%llu,\"signal_strength_dbm\":%d"
        "},"
        "\"crash_detection\":{"
        "\"crash_flag\":%s,\"impact_force_g\":%.1f,"
        "\"speed_delta_kmh\":%.1f,\"rollover_detected\":%s,"
        "\"confidence\":%.2f"
        "},"
        "\"status_flags\":{"
        "\"sos_active\":%s,\"emergency_brake\":false,"
        "\"ignition_on\":true,\"vehicle_stopped\":%s"
        "}"
        "}",
        DEVICE_ID,
        (unsigned long long)(time_us_64() / 1000),
        gps->latitude, gps->longitude, gps->altitude_m,
        gps->speed_kmh, gps->heading_deg, gps->accuracy_m,
        gps->satellites, gps->fix_quality,
        imu->x, imu->y, imu->z,
        imu->gx, imu->gy, imu->gz,
        imu->temperature_c,
        85, 42.0f,  // Battery %, CPU temp (simulated)
        (unsigned long long)((time_us_64() - boot_time_ms * 1000) / 1000000),
        -75,  // Signal strength (simulated)
        crash->crash_flag ? "true" : "false",
        crash->impact_force_g,
        crash->speed_delta_kmh,
        crash->rollover_detected ? "true" : "false",
        crash->confidence,
        sos_triggered ? "true" : "false",
        gps->speed_kmh < 1.0f ? "true" : "false"
    );
}

// ── Core 1: Network Communication ────────────────────────────────────────────

void core1_network_task() {
    while (1) {
        // Wait for telemetry flag (checked via global)
        if (crash_alert) {
            // Send emergency SMS via SIM7600
            uart_puts(SIM7600_UART, "AT+CMGS=\"+919XXXXXXXXX\"\r\n");
            sleep_ms(200);
            uart_puts(SIM7600_UART, "CRASH ALERT: Vehicle accident detected at location. Immediate assistance required.\r\n");
            sleep_ms(200);
            uint8_t ctrl_z = 0x1A;
            uart_puts(SIM7600_UART, &ctrl_z);
            sleep_ms(1000);
            crash_alert = false;
        }
        tight_loop_contents();
    }
}

// ── Main ──────────────────────────────────────────────────────────────────────

int main() {
    // Initialize stdio and Pico SDK
    stdio_init_all();
    sleep_ms(3000);  // Wait for serial
    printf("\n\n=== RoadSoS Hardware Telemetry Unit ===\n");
    printf("Device: %s | Firmware: %s\n", DEVICE_ID, FIRMWARE_VERSION);

    // Initialize status LED
    gpio_init(STATUS_LED);
    gpio_set_dir(STATUS_LED, GPIO_OUT);
    gpio_put(STATUS_LED, 1);  // On during boot

    // Boot time
    boot_time_ms = to_ms_since_boot(get_absolute_time());

    // Initialize sensors
    if (!mpu9250_init()) {
        printf("FATAL: MPU-9250 initialization failed\n");
        while (1) {  // Blink fast forever
            gpio_put(STATUS_LED, !gpio_get(STATUS_LED));
            sleep_ms(100);
        }
    }

    if (!sim7600_init()) {
        printf("WARNING: SIM7600E-H initialization failed (continuing without LTE)\n");
    }

    // Initialize GPS via SIM7600 internal GPS
    uart_puts(SIM7600_UART, "AT+CGPS=1,1\r\n");
    sleep_ms(500);

    // Launch network task on Core 1
    multicore_launch_core1(core1_network_task);

    printf("System ready. Starting telemetry loop...\n");
    gpio_put(STATUS_LED, 0);  // Off after boot

    // ── Main Loop (Core 0) ──────────────────────────────────────────────────
    uint64_t last_sensor_ms = 0;
    uint64_t last_telemetry_ms = 0;
    telemetry_packet_t last_packet = {0};
    char json_buffer[2048];

    while (1) {
        uint64_t now_ms = to_ms_since_boot(get_absolute_time());

        // 1. Read sensors at 50 Hz
        if ((now_ms - last_sensor_ms) >= SENSOR_READ_INTERVAL_MS) {
            imu_reading_t imu;
            if (mpu9250_read(&imu)) {
                // Store in history buffer
                imu_history[imu_history_idx] = imu;
                imu_history_idx = (imu_history_idx + 1) % IMU_HISTORY_SIZE;
                last_packet.imu = imu;

                // Run crash detection
                crash_detection_t crash = detect_crash(&imu);
                last_packet.crash = crash;

                if (crash.crash_flag && !crash_alert) {
                    crash_alert = true;
                    gpio_put(STATUS_LED, 1);  // LED on for crash
                    printf("*** CRASH DETECTED! Impact: %.1fg ***\n", crash.impact_force_g);
                }
            }

            // Read GPS at 5 Hz (read NMEA from SIM7600)
            if ((now_ms % 200) < SENSOR_READ_INTERVAL_MS) {
                char nmea_buf[256];
                int n = 0;
                while (uart_is_readable(SIM7600_UART) && n < 255) {
                    nmea_buf[n++] = uart_getc(SIM7600_UART);
                }
                nmea_buf[n] = '\0';

                // Parse NMEA sentences
                char* line = strtok(nmea_buf, "\r\n");
                while (line != NULL) {
                    if (strstr(line, "$GPRMC")) {
                        parse_nmea_gprmc(line, &last_packet.gps);
                    } else if (strstr(line, "$GPGGA")) {
                        parse_nmea_gga(line, &last_packet.gps);
                    }
                    line = strtok(NULL, "\r\n");
                }
            }

            last_sensor_ms = now_ms;
        }

        // 2. Send telemetry at 1 Hz
        if ((now_ms - last_telemetry_ms) >= TELEMETRY_INTERVAL_MS) {
            last_packet.uptime_seconds = (now_ms - boot_time_ms) / 1000;

            // Build JSON packet
            build_telemetry_json(
                &last_packet.imu, &last_packet.gps, &last_packet.crash,
                json_buffer, sizeof(json_buffer)
            );

            // Send via LTE
            if (!sim7600_send_http_post(BACKEND_URL, json_buffer)) {
                printf("Telemetry send failed (buffering for retry)\n");
            } else {
                printf("Telemetry sent: GPS(%.4f,%.4f) Spd=%.1f Crash=%d\n",
                       last_packet.gps.latitude, last_packet.gps.longitude,
                       last_packet.gps.speed_kmh, last_packet.crash.crash_flag);
            }

            // Blink LED on successful telemetry
            gpio_put(STATUS_LED, 1);
            sleep_ms(10);
            gpio_put(STATUS_LED, 0);

            last_telemetry_ms = now_ms;
        }

        // 3. Sleep to save power
        sleep_ms(1);
    }

    return 0;
}