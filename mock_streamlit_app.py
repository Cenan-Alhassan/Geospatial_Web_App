import streamlit as st
import pandas as pd
import numpy as np # Used here to generate random data, but Pandas is the core
import os

st.title("🌎 Dealing with vector data (GeoPandas and Pydeck)")

st.header("Dataframe from Pandas")
# 1. Create a DataFrame with mock coordinates
data = {
    'lat': [34.0522, 40.7128, 51.5074, 39.9042], # Mock latitudes (LA, NY, London, Beijing)
    'lon': [-118.2437, -74.0060, 0.1278, 116.4074], # Mock longitudes
    'label': ['LA', 'NY', 'London', 'Beijing']
}
df = pd.DataFrame(data)

st.dataframe(df) # Display the raw DataFrame

# 2. Add the map visualization
st.header("Training Data Points (Map)")
st.map(df) # Streamlit automatically looks for 'lat', 'lon', 'latitude', or 'longitude'

st.write("Welcome to the first version of the map viewer!")


import geopandas as gpd
import json
from io import StringIO
st.header("GeoDataFrame from GeoPandas")

# --- 1. Mock Vector Data (representing a Polygon) ---
# This GeoJSON represents a simple square (a region of interest)
geojson_data = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"id": 1, "area_name": "Training Zone A"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-118.3, 34.0], [-118.2, 34.0], [-118.2, 34.1], [-118.3, 34.1], [-118.3, 34.0]]]
            }
        }
    ]
}

# --- 2. Read the GeoJSON string into a GeoDataFrame ---
# We use gpd.read_file() with a buffer object (StringIO) to simulate reading a file
# The code below converts the GeoJSON dictionary into a file-like object for reading
geojson_str = json.dumps(geojson_data)
gdf = gpd.read_file(StringIO(geojson_str))

gdf['lat'] = gdf.geometry.centroid.y
gdf['lon'] = gdf.geometry.centroid.x
gdf_4326 = gdf.to_crs(epsg=4326)

st.subheader("Vector Training Data (GeoDataFrame)")
st.dataframe(gdf_4326)

st.map(gdf_4326)


import pydeck

center_lon = gdf_4326.geometry.centroid.x.mean() # get mean of centroids of all geometries
center_lat = gdf_4326.geometry.centroid.y.mean()
st.header('Trying a GeoJsonLayer with Pydeck')

# 1. Define the layer, pointing it at our data
polygon_layer = pydeck.Layer(
    "GeoJsonLayer",
    data=gdf_4326, # This will be the prepared GeoJSON data
    filled=True,
    get_fill_color=[200, 30, 0, 160], # RGBA color for the polygon fill
    get_line_color=[0, 0, 0],
    line_width_min_pixels=2,
)

# 2. Define the view and render the map
view_state = pydeck.ViewState(
    latitude=center_lat, # Centered on our data's location
    longitude=center_lon,
    zoom=11,
)

st.pydeck_chart(pydeck.Deck(layers=[polygon_layer], initial_view_state=view_state))


st.title("🌎 Dealing with raster data (Rasterio and URL)")

import rasterio

# --- 1. Raster Data Bounds Extraction ---
RASTER_FILE_PATH = "ml_output.tif"
RASTER_IMAGE_URL = "http://YOUR_SERVER_ADDRESS/temp/ml_output.png" # <--- MISSING LINK

try:
    with rasterio.open(RASTER_FILE_PATH, 'r') as src:
        bounds = src.bounds
        raster_bounds_list = [bounds.left, bounds.bottom, bounds.right, bounds.top]

        # Define the BitmapLayer for the ML Output
        raster_layer = pdk.Layer(
            "BitmapLayer",
            image=RASTER_IMAGE_URL,
            bounds=raster_bounds_list,
            opacity=0.8
        )
        
except rasterio.errors.RasterioIOError:
    # If the file doesn't exist yet, we can skip the raster layer for now
    raster_layer = None


# --- 2. Combining Layers ---
layers = [polygon_layer] # Start with the vector training data layer
if raster_layer:
    layers.append(raster_layer) # Add the ML output if the bounds were found

# --- 3. Render Deck ---
# Center and View State logic based on combined bounds...
st.pydeck_chart(pydeck.Deck(layers=layers, initial_view_state=view_state))