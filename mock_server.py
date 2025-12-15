# server.py
from flask import Flask
import os

# 1. Create the static folder if it doesn't exist
if not os.path.exists('static'):
    os.makedirs('static')

# ↓ Defining the app

# 2. Initialize Flask, pointing to the 'static' folder (relative to this script)
app = Flask(__name__, static_folder='static') ### Create the app instance, with name and the folder you expose

YOUR_SERVER_ADDRESS = 'localhost:5000'


# ↓ Define a url, and what it does when the url is accessed
@app.route('/') ### The decorator (@app.route('/')) tells Flask: "Whenever a user visits the root URL of this server (/), execute the function immediately below it (home()) and return the result to the user's browser
def home():
    # Streamlit will read the image from this public URL
    # IMPORTANT: The Flask app runs on port 5000 by default
    image_url = f'http://{YOUR_SERVER_ADDRESS}/static/ml_output.png'
    return f"The image is served at: {image_url}"


@app.route('/static')
def sus():
    return 'lol'

# ↓ Running the app

# 3. Run the server locally on port 5000
if __name__ == '__main__':
    # We must run this in a SEPARATE terminal from Streamlit
    app.run(port=5000) ### tells the computer to open network port 5000 and listen for requests




"""

# server.py (Snippet for image generation)
import rasterio
from PIL import Image
import numpy as np
# ... [Flask and os imports] ...

# 1. Define placeholder paths
GEO_TIFF_PATH = 'data/ml_output.tif' # We'll assume a 'data' folder for source files
PNG_OUTPUT_PATH = 'static/ml_output.png'

def generate_and_serve_image():
    # Load and process the GeoTIFF
    with rasterio.open(GEO_TIFF_PATH) as src:
        # Read the first band of pixel data (your ML output values)
        data = src.read(1) 
        
        # Normalize the data (Crucial step for visualization! Scales values from 0-255)
        # This assumes your ML output is a single band (e.g., probability)
        data = (data - data.min()) / (data.max() - data.min()) * 255
        
        # 2. Convert to an 8-bit unsigned integer array (required for basic image formats)
        data_int8 = data.astype(np.uint8)

        # 3. Create the Pillow Image object
        img = Image.fromarray(data_int8, mode='L') # 'L' mode for grayscale (single band)

        # 4. Save the image to the static folder for Flask to serve
        img.save(PNG_OUTPUT_PATH, 'PNG')

        # NOTE: We still need to extract the bounds for Streamlit's Pydeck chart!
        bounds = src.bounds
        return [bounds.left, bounds.bottom, bounds.right, bounds.top] # Return bounds to the caller

"""