import os
import json
from flask import Flask, jsonify, send_file
from PIL import Image
import geopandas as gpd
import rasterio
from rasterio.warp import transform_bounds
import numpy as np

# ----------------- CORS CHANGE -----------------
from flask_cors import CORS # 1. Import CORS
# -----------------------------------------------

# 1. Configuration: Define the secure, hidden data folder path
# This folder is NOT publicly accessible.
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_storage')

# Initialize the Flask application
app = Flask(__name__)
CORS(app)

# --------------------------------------------------------------------------
# --- UPDATED RASTER PROCESSING FUNCTION (Now real) ---
# --------------------------------------------------------------------------

import os
import numpy as np
import rasterio # Need this
# from PIL import Image # No longer strictly needed if only using Rasterio write

def process_tif_to_png(file_path):
    """
    Reads the TIF, applies robust scaling by ignoring the NoData value 
    and matching the 1-4 data range, and writes a valid PNG file.
    """
    if not os.path.exists(file_path):
        return None, "Raster source file not found."

    # Define the path for the temporary output PNG file
    temp_png_path = file_path.replace('.tif', '_temp_output.png')

    try:
        with rasterio.open(file_path) as src:
            # 1. Read the array and get the NoData value
            image_array = src.read(1)
            nodata_val = src.nodata
            
            # --- ROBUST SCALING LOGIC (Handles UInt32 and NoData) ---
            
            # Find the actual min/max of the VALID data by excluding NoData
            if nodata_val is not None:
                # Use a masked array to exclude NoData from calculations
                # NOTE: numpy.ma handles the large UInt32 NoData value correctly
                valid_data = np.ma.masked_equal(image_array, nodata_val)
                min_val = np.min(valid_data)
                max_val = np.max(valid_data)
            else:
                # Fallback if NoData is not explicitly set
                min_val = np.min(image_array)
                max_val = np.max(image_array)

            # 2. Check the data range (should be 1 to 4)
            range_val = max_val - min_val
            
            if range_val <= 0:
                 return None, "TIF data is uniform (single class) and cannot be scaled."

            # 3. Apply the scaling: (data - min) / (range) * 255
            # This scales the 1-4 range to 0-255
            image_array_scaled = ((image_array - min_val) / range_val) * 255
            
            # 4. Convert to 8-bit integer type
            image_array_8bit = image_array_scaled.astype(np.uint8)

            # 5. Re-apply the NoData mask to the 8-bit array (setting NoData pixels to 0)
            if nodata_val is not None:
                image_array_8bit[image_array == nodata_val] = 0 
            
            # --- PNG WRITING ---
            out_profile = src.profile
            out_profile.update(
                dtype=rasterio.uint8, 
                count=1,          # Single band (Grayscale)
                driver='PNG',
                nodata=0          # Set NoData to 0 in the output PNG
            )

            with rasterio.open(temp_png_path, 'w', **out_profile) as dst:
                # Write the 8-bit array as band 1
                dst.write(image_array_8bit, 1)

            # --- INTEGRITY CHECK ---
            try:
                img_check = Image.open(temp_png_path)
                print(f"DEBUG: Saved PNG dimensions check: {img_check.size}")
                img_check.close()
            except Exception as e:
                # This should no longer happen!
                return None, f"FATAL ERROR: Saved file is corrupt after processing: {e}"
            
        return temp_png_path, None
    
    except Exception as e:
        return None, f"Error processing TIF to PNG: {e}"
    
def get_geojson_data(file_path):
    """
    Reads the vector file (GPKG/SHP/GeoJSON), converts it to GeoJSON string,
    then loads it into a dictionary for Flask's jsonify().
    """
    if not os.path.exists(file_path):
        return None, "Vector source file not found."
    
    try:
        # 1. Read the vector file into a GeoDataFrame
        gdf = gpd.read_file(file_path)
        
        # 2. Convert GeoDataFrame to a GeoJSON string
        geojson_str = gdf.to_json()
        
        # 3. Convert the GeoJSON string back into a Python dictionary
        geo_data_dict = json.loads(geojson_str)
        
        return geo_data_dict, None
    
    except Exception as e:
        return None, f"Error processing vector file: {e}"


# --------------------------------------------------------------------------
# --- Main Dynamic Route Handler ---
# --------------------------------------------------------------------------

@app.route('/api/get-data/<run_id>/<file_name>')
def get_data(run_id, file_name):
    # 1. Construct the full, hidden file path
    full_path = os.path.join(DATA_FOLDER, run_id, file_name)

    # 2. Extract the file extension
    # [1] extracts the extension (e.g., '.tif', '.geojson')
    file_ext = os.path.splitext(file_name)[1].lower()

    if file_ext == '.tif':
        # --- RASTER PATH: Transform and Send Binary Data (PNG) ---
        png_path, error = process_tif_to_png(full_path)
        
        if error:
            return jsonify({"error": error}), 500
        
        # send_file is for binary data (images, PDFs, etc.)
        # We send the processed PNG, not the raw TIF
        return send_file(png_path, mimetype='image/png')
        
    elif file_ext in ('.geojson', '.gpkg', '.shp'):
        # --- VECTOR PATH: Transform and Send Structured Data (GeoJSON) ---
        geo_data, error = get_geojson_data(full_path)
        
        if error:
            return jsonify({"error": error}), 500
            
        # jsonify is for text/structured data
        return jsonify(geo_data)

    else:
        # --- UNSUPPORTED FILE TYPE ---
        return jsonify({"error": f"Unsupported file type requested: {file_ext}"}), 400

# --------------------------------------------------------------------------
# --- Acquire Metadata of Raster ---
# --------------------------------------------------------------------------

@app.route('/api/metadata/<run_id>/<file_name>')
def get_metadata(run_id, file_name):
    """
    Reads the TIF file header (using Rasterio), extracts bounds, 
    and transforms them to EPSG:4326 (the web standard).
    """
    full_path = os.path.join(DATA_FOLDER, run_id, file_name)
    
    if not os.path.exists(full_path):
        return jsonify({"error": "Raster source file not found."}), 404
    
    try:
        with rasterio.open(full_path) as src:
            # 1. Transform the bounds from the TIF's native CRS to EPSG:4326
            # The order is: src_crs, dst_crs, west, bottom, right, top
            wgs84_bounds = transform_bounds(
                src_crs=src.crs, 
                dst_crs='EPSG:4326', 
                left=src.bounds.left, 
                bottom=src.bounds.bottom, 
                right=src.bounds.right, 
                top=src.bounds.top
            )

            # 2. Package the reprojected bounds for the client
            metadata = {
                # We return the bounds in the required [W, S, E, N] format
                "bounds": list(wgs84_bounds), 
                "crs": f'original: {src.crs.to_string()}, converted to EPSG:4326',
                "file_type": "raster"
            }
            return jsonify(metadata)
            
    except Exception as e:
        return jsonify({"error": f"Error reading TIF metadata: {e}"}), 500


@app.route('/')
def home():
    return "Welcome"


# --------------------------------------------------------------------------
# --- Run the Server ---
# --------------------------------------------------------------------------
if __name__ == '__main__':
    # Creates the data_storage folder if it doesn't exist for testing
    os.makedirs(DATA_FOLDER, exist_ok=True) 
    print(f"Server data path set to: {DATA_FOLDER}")
    # Run on a different port than Streamlit (Streamlit often uses 8501)
    app.run(debug=True, port=5000)