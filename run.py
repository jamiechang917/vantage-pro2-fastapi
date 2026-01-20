import uvicorn
from fastapi import FastAPI
from threading import Thread, Lock
import time
from weather_station import fetch_all_data

# --- Global Cache and Lock ---
# This dictionary will hold the latest weather data
weather_data_cache = {
    "liveData": None,
    "hiLowData": None,
    "consoleInfo": None,
    "error": "Data is being fetched for the first time. Please wait..."
}
# A lock to ensure only one thread accesses the cache at a time
cache_lock = Lock()

# --- FastAPI App ---
app = FastAPI(
    title="Vantage Pro2 Weather API",
    description="Provides live and summary data from a Davis Vantage Pro2 weather station.",
    version="1.0.0"
)

# --- Background Task ---
def update_weather_data_periodically():
    """
    A function to be run in a background thread.
    It calls fetch_all_data() every 60 seconds and updates the cache.
    """
    global weather_data_cache
    while True:
        print("[INFO] Background thread: Fetching new weather data...")
        data = fetch_all_data()
        
        with cache_lock:
            weather_data_cache = data
        
        print("[INFO] Background thread: Cache updated. Sleeping for 5 seconds.")
        time.sleep(5) # Wait 5 seconds before fetching again

# --- API Endpoint ---
@app.get("/data")
def get_data():
    """
    Returns the most recent weather data from the cache.
    The cache is updated by a background thread every 60 seconds.
    """
    with cache_lock:
        return weather_data_cache

# --- Server Startup ---
if __name__ == "__main__":
    # Start the background thread on a separate daemon thread
    # This means it will stop when the main app stops
    print("[INFO] Starting background data-fetching thread...")
    data_thread = Thread(target=update_weather_data_periodically, daemon=True)
    data_thread.start()
    
    # Start the FastAPI server
    print("[INFO] Starting FastAPI server on http://0.0.0.0:8888")
    uvicorn.run(app, host="0.0.0.0", port=8888)