import streamlit as st
import pyautogui
import time
from datetime import datetime
import os
import threading
from PIL import Image
import pytesseract
import re

# Global variables
stop_flag = False
max_screenshots = 100  # Maximum number of screenshots to keep
screenshot_dir = "screenshots"  # Hardcoded directory for screenshots
screenshot_interval = 10  # in seconds

# File to store OCR descriptions
ocr_data_file = screenshot_dir + "/ocr_descriptions.txt"

# Initialize the screenshot directory if it doesn't exist
if not os.path.exists(screenshot_dir):
    os.makedirs(screenshot_dir)

def screenshot_timer():
    """Take screenshots every 10 seconds until stopped."""
    global stop_flag
    while not stop_flag:
        # Generate a timestamped filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(screenshot_dir, f"screenshot_{timestamp}.png")

        # Take a screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)

        # Perform OCR and save description
        description = perform_ocr(filename)
        save_description(filename, description)

        # Limit the number of screenshots
        enforce_rolling_screenshots()

        st.write(f"Saved screenshot: {filename} with description: {description}")

        # Wait for interval seconds
        time.sleep(screenshot_interval)


def perform_ocr(image_path):
    """Extract text from an image using OCR and clean it."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)

    # Remove newlines and extra spaces
    cleaned_text = text.strip()  # Strip leading/trailing spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Replace multiple spaces with a single space
    cleaned_text = cleaned_text.replace("\n", " ")  # Replace newlines with spaces

    return cleaned_text


def save_description(image_path, description):
    """Save the screenshot filename and description to a file."""
    with open(ocr_data_file, "a") as f:
        f.write(f"{os.path.basename(image_path)}<-----delimiter-----> {description}\n")


def load_descriptions():
    """Load screenshot descriptions from the file."""
    if not os.path.exists(ocr_data_file):
        return {}
    with open(ocr_data_file, "r") as f:
        lines = f.readlines()
    return {line.split("<-----delimiter----->")[0]: line.split("<-----delimiter----->", 1)[1].strip() for line in lines}


def enforce_rolling_screenshots():
    """Ensure only the last `max_screenshots` are kept in the directory and descriptions are deleted."""
    files = sorted(
        [os.path.join(screenshot_dir, f) for f in os.listdir(screenshot_dir) if f.endswith(".png")],
        key=os.path.getctime
    )

    # If there are more files than max_screenshots, delete old files and their descriptions
    if len(files) > max_screenshots:
        # Load existing descriptions
        descriptions = load_descriptions()

        for file_to_delete in files[:-max_screenshots]:
            # Delete the screenshot
            os.remove(file_to_delete)
            st.write(f"Deleted old screenshot: {file_to_delete}")

            # Delete the description from the OCR data file
            file_name = os.path.basename(file_to_delete)
            if file_name in descriptions:
                delete_description(file_name)
                st.write(f"Deleted description for screenshot: {file_name}")


def delete_description(filename):
    """Delete the description corresponding to the given filename from the OCR data file."""
    with open(ocr_data_file, "r") as f:
        lines = f.readlines()

    with open(ocr_data_file, "w") as f:
        for line in lines:
            if not line.startswith(filename):
                f.write(line)


def search_screenshots(query, descriptions):
    """Search for screenshots by query in descriptions."""
    results = [
        filename for filename, desc in descriptions.items() if query.lower() in desc.lower()
    ]
    return results


# Streamlit UI
st.title("Screenshot Timer with OCR, Search, and Fixed Directory")

# Display the hardcoded screenshot directory
st.write(f"Screenshots will be stored in: {screenshot_dir}")

# Start/Stop buttons
if "is_running" not in st.session_state:
    st.session_state.is_running = False

if st.button("Start Screenshot Timer"):
    if not st.session_state.is_running:
        stop_flag = False
        st.session_state.is_running = True
        threading.Thread(target=screenshot_timer, daemon=True).start()
        st.write("Screenshot timer started!")

if st.button("Stop Screenshot Timer"):
    if st.session_state.is_running:
        stop_flag = True
        st.session_state.is_running = False
        st.write("Screenshot timer stopped.")

# Search functionality
st.write("### Search Screenshots")
descriptions = load_descriptions()
search_query = st.text_input("Enter search query:")

if search_query:
    search_results = search_screenshots(search_query, descriptions)
    if search_results:
        st.write(f"Found {len(search_results)} matching screenshots:")
        for result in search_results:
            st.image(os.path.join(screenshot_dir, result), caption=result)
    else:
        st.write("No matching screenshots found.")

# Timeline Viewer
st.write("### Timeline Viewer")

screenshot_files = list(descriptions.keys())
if screenshot_files:
    selected_index = st.slider(
        "Select a screenshot by timestamp:",
        0,
        len(screenshot_files) - 1,
        step=1,
        format=f"Screenshot %d of {len(screenshot_files)}"
    )
    selected_file = screenshot_files[selected_index]
    st.image(
        os.path.join(screenshot_dir, selected_file),
        caption=f"Screenshot: {selected_file}\nDescription: {descriptions[selected_file]}"
    )
else:
    st.write("No screenshots available yet. Start the timer to capture screenshots.")
