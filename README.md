# Vantage Pro2 FastAPI Bridge

This project provides a lightweight, modern web interface for the **Davis Vantage Pro2** weather station. 

It connects to the weather console via a serial interface (USB/Serial adapter), fetches live weather data (LOOP packets) and high/low records (HILOWS packets) in the background, and exposes the data via a JSON REST API using **FastAPI**.

## Features

* **Real-time Data:** Fetches standard weather metrics (Temperature, Humidity, Wind Speed/Direction, Rain, Barometer) via LOOP packets.
* **High/Low Records:** Retrieves daily, monthly, and yearly highs and lows via HILOWS packets.
* **Background Caching:** Runs a background thread to fetch data every 60 seconds, ensuring API requests are instant and do not block the serial bus.
* **JSON API:** Simple REST endpoint for easy integration with frontend dashboards, Home Assistant, or other monitoring tools.

## Prerequisites

* **Hardware:**
    * Davis Vantage Pro2 Console.
    * WeatherLink Serial Adapter (or compatible USB-to-Serial cable).
    * A computer/server running Python (Raspberry Pi, Linux VM, Windows, or Mac).
* **Software:**
    * Python 3.8+

## Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/jamiechang917/vantage-pro2-fastapi.git](https://github.com/jamiechang917/vantage-pro2-fastapi.git)
    cd vantage-pro2-fastapi
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before running the server, you must configure the serial port settings to match your hardware.

1.  Open `weather_station.py`.
2.  Locate the **Configuration** section near the top:
    ```python
    # --- Configuration ---
    # Update this to your station's serial port
    SERIAL_PORT = 'COM3'  # Windows example
    # SERIAL_PORT = '/dev/ttyUSB0'  # Linux/Raspberry Pi example
    BAUD_RATE = 19200
    ```
3.  Change `SERIAL_PORT` to the correct port for your system.

## Usage

### 1. Run the Server
Start the application using the `run.py` entry point. This will launch the background data fetcher and the FastAPI web server.

```bash
python run.py
```
You should see output indicating the background thread has started and the server is listening:

```
[INFO] Starting background data-fetching thread...
[INFO] Starting FastAPI server on [http://0.0.0.0:8888](http://0.0.0.0:8888)
[INFO] Background thread: Fetching new weather data...
```

### 2. Access the Data
Open your web browser or use curl to access the API:

- API Endpoint: http://localhost:8888/data

- Interactive Docs: http://localhost:8888/docs

Example JSON Response:

```json
{
  "liveData": {
    "barometerHpa": 1013.2,
    "outsideTempC": 24.5,
    "windSpeedMs": 3.2,
    "windDirectionText": "NW",
    "dailyRainMm": 0.0,
    ...
  },
  "hiLowData": {
    "outTempDayHighC": 28.1,
    "windDayHighMs": 8.5,
    ...
  },
  "consoleInfo": {
    "consoleTime": "2023-10-27 14:30:00",
    "firmwareVersion": "1.90"
  }
}
```
## Deployment (Optional)
If you are running this on a Linux server (e.g., Raspberry Pi or Ubuntu) and want it to run automatically at startup, you can create a Systemd service.
1. Create a file at `/etc/systemd/system/weather-api.service`:
```Ini,TOML
[Unit]
Description=Vantage Pro2 Weather API
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/vantage-pro2-fastapi
ExecStart=/usr/bin/python3 /path/to/vantage-pro2-fastapi/run.py
Restart=always

[Install]
WantedBy=multi-user.target
```
2. Enable and start the service:
```bash
sudo systemctl enable weather-api
sudo systemctl start weather-api
```
