import streamlit as st
import pyautogui
import time
from datetime import datetime
import os
import threading
from PIL import Image
import pytesseract
import json

# Snapshot directory
snapshot_dir = "snapshots"
os.makedirs(snapshot_dir, exist_ok=True)

# Snapshot interval in seconds
snapshot_interval = 10

# Settings file path
settings_file = "settings.json"

# Initialize settings if not present
default_settings = {
    "stop_flag": True,
    "is_running": False,
    "max_snapshots": 100,
}

if not os.path.exists(settings_file):
    with open(settings_file, "w") as f:
        json.dump(default_settings, f)

# Helper functions to manage settings
def read_settings():
    with open(settings_file, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=4)

# OCR descriptions file
ocr_data_file = os.path.join(snapshot_dir, "ocr_descriptions.txt")

def perform_ocr(image_path):
    """Extract text from an image using OCR."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.replace("\n", " ").strip()

def save_description(image_path, description):
    """Save the snapshot filename and description to a file."""
    with open(ocr_data_file, "a") as f:
        f.write(f"{os.path.basename(image_path)}<-----delimiter----->{description}\n")

def load_descriptions():
    """Load snapshot descriptions from the file."""
    if not os.path.exists(ocr_data_file):
        return {}
    with open(ocr_data_file, "r") as f:
        lines = f.readlines()
    return {
        line.split("<-----delimiter----->")[0]: line.split("<-----delimiter----->", 1)[1].strip()
        for line in lines
    }

def enforce_rolling_snapshots(max_snapshots):
    """Ensure only the last `max_snapshots` are kept in the directory and descriptions are deleted."""
    files = sorted(
        [os.path.join(snapshot_dir, f) for f in os.listdir(snapshot_dir) if f.endswith(".png")],
        key=os.path.getctime,
    )

    # If there are more files than max_snapshots, delete old files and their descriptions
    if len(files) > max_snapshots:
        descriptions = load_descriptions()

        for file_to_delete in files[:-max_snapshots]:
            os.remove(file_to_delete)

            # Delete the description from the OCR data file
            file_name = os.path.basename(file_to_delete)
            if file_name in descriptions:
                delete_description(file_name)

def delete_description(filename):
    """Delete the description corresponding to the given filename from the OCR data file."""
    with open(ocr_data_file, "r") as f:
        lines = f.readlines()
    with open(ocr_data_file, "w") as f:
        for line in lines:
            if not line.startswith(filename):
                f.write(line)

def snapshot_timer():
    """Take snapshots every interval seconds until stopped, checking the latest settings."""
    while True:
        settings = read_settings()
        if settings["stop_flag"]:
            break  # Exit the loop if the stop flag is set

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(snapshot_dir, f"snapshot_{timestamp}.png")

        # Take a snapshot
        snapshot = pyautogui.screenshot()
        snapshot.save(filename)

        # Perform OCR and save description
        description = perform_ocr(filename)
        save_description(filename, description)

        # Limit the number of snapshots
        enforce_rolling_snapshots(settings["max_snapshots"])

        time.sleep(snapshot_interval)

# Streamlit UI
st.title("Recall")

# Left panel for controls
with st.sidebar:
    st.header("Service Controls")

    # Show service state
    settings = read_settings()
    state_message = "Running" if settings["is_running"] else "Stopped"
    st.write(f"Service State: **{state_message}**")

    # Input box for maximum snapshots
    max_snapshots = st.number_input(
        "Max snapshots to keep:",
        min_value=1,
        max_value=1000,
        value=settings["max_snapshots"],
        step=1,
    )

    if st.button("Save Settings"):
        settings = read_settings()
        settings["max_snapshots"] = max_snapshots
        save_settings(settings)
        st.write("Settings saved!")

    # Start/Stop buttons
    if st.button("Start Snapshot Timer"):
        settings = read_settings()
        if not settings["is_running"]:
            settings["stop_flag"] = False
            settings["is_running"] = True
            save_settings(settings)

            # Start a new thread for snapshot timer
            threading.Thread(target=snapshot_timer, daemon=True).start()
            st.write("Snapshot timer started!")

    if st.button("Stop Snapshot Timer"):
        settings = read_settings()
        if settings["is_running"]:
            settings["stop_flag"] = True
            settings["is_running"] = False
            save_settings(settings)
            st.write("Snapshot timer stopped.")

# Main app UI
st.header("Snapshot Viewer")

# Search snapshots
st.subheader("Search Snapshots")
search_query = st.text_input("Enter search query:")
descriptions = load_descriptions()

if search_query:
    search_results = [
        filename for filename, desc in descriptions.items() if search_query.lower() in desc.lower()
    ]
    if search_results:
        st.write(f"Found {len(search_results)} matching snapshots:")
        for result in search_results:
            st.image(os.path.join(snapshot_dir, result), caption=result)
    else:
        st.write("No matching snapshots found.")

# Timeline viewer
st.subheader("Timeline Viewer")
snapshot_files = sorted(descriptions.keys())

if snapshot_files:
    start_time = snapshot_files[0].replace("snapshot_", "").replace(".png", "")
    end_time = snapshot_files[-1].replace("snapshot_", "").replace(".png", "")

    start_time_formatted = datetime.strptime(start_time, "%Y-%m-%d_%H-%M-%S").strftime(
        "%A, %B %d, %Y • %H:%M:%S"
    )
    end_time_formatted = datetime.strptime(end_time, "%Y-%m-%d_%H-%M-%S").strftime(
        "%A, %B %d, %Y • %H:%M:%S"
    )

    st.write(f"Timeline: {start_time_formatted} — {end_time_formatted}")

    selected_index = st.slider(
        "Select a snapshot by timestamp:",
        0,
        len(snapshot_files) - 1,
        step=1,
        )
    selected_file = snapshot_files[selected_index]
    selected_path = os.path.join(snapshot_dir, selected_file)

    timestamp = datetime.strptime(
        selected_file.replace("snapshot_", "").replace(".png", ""),
        "%Y-%m-%d_%H-%M-%S",
    )
    formatted_date = timestamp.strftime("%A, %B %d, %Y • %H:%M:%S")

    st.image(selected_path, caption=f"Snapshot: {selected_file}\nDate: {formatted_date}")
else:
    st.write("No snapshots available yet. Start the timer to capture snapshots.")
