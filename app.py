import streamlit as st
import requests
import geopandas as gpd
import pydeck as pdk
import json
from io import StringIO

# --- Configuration ---
# Assuming the Flask server is running locally on port 5000
BASE_URL = 'http://127.0.0.1:5000/api/get-data'
METADATA_URL = 'http://127.0.0.1:5000/api/metadata'
# We are currently using a fixed Run ID for demonstration
RUN_ID = 'test' 

st.title("🗺️ ML Geo-Visualization Client")

# --- UI Input ---
# The user only needs to provide the file name part of the URL (e.g., 'vector.geojson')
file_name = st.text_input(
    "Enter File Name to Request (e.g., testing.gpkg):",
    value="testing.gpkg"
)

# --- API Call and Processing ---
if file_name:
    full_url = f"{BASE_URL}/{RUN_ID}/{file_name}"
    
    # 1. Make the API Request
    st.info(f"Requesting data from: {full_url}")
    response = requests.get(full_url)

    # 2. Check for Successful Response (CRITICAL STEP)
    if response.status_code == 200:

        st.success("Data successfully received from API.")
        content_type = response.headers.get('Content-Type') # Get the MIME type from the response to see if it is JSON or binary
        

        #1 --- VECTOR PATH ---
        if 'application/json' in content_type:
            try:
                # 3. Retrieve GeoJSON Data
                # response.json() converts the JSON string to a Python dictionary
                geo_data_dict = response.json()
                
                # 4. Convert Dictionary to GeoDataFrame using the in-memory method
                # We convert the dict back to a string, then treat the string as a file
                geojson_str = json.dumps(geo_data_dict)
                gdf = gpd.read_file(StringIO(geojson_str))

                # --- FIX: Convert CRS to Web Standard (EPSG:4326) ---
                # This ensures the coordinates are valid Lat/Lon for PyDeck
                gdf = gdf.to_crs(epsg=4326) 
                # ---------------------------------------------------

                st.dataframe(gdf.head()) # Show a snippet of the data
                
                # --- 5. Visualization using PyDeck ---
                
                # Use the centroid of the data as the initial view center
                center_lat = gdf.geometry.centroid.y.mean()
                center_lon = gdf.geometry.centroid.x.mean()
                
                # Define the map layers (using a GeoJsonLayer for vector data)
                layer = pdk.Layer(
                    'GeoJsonLayer',
                    data=gdf,
                    opacity=0.8,
                    stroked=True,
                    filled=True,
                    extruded=False,
                    get_fill_color=[180, 0, 200, 140], # Purple color
                    get_line_color=[255, 255, 255],
                )

                # Define the initial view state
                view_state = pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=10,
                    pitch=0
                )

                # Render the PyDeck map in Streamlit
                st.pydeck_chart(pdk.Deck(
                    map_style='light',
                    initial_view_state=view_state,
                    layers=[layer],
                ))

            except Exception as e:
                st.error(f"Error during data processing or visualization: {e}")


        #2 --- RASTER PATH (TWO-STEP PROCESS) ---
        elif 'image/png' in content_type:
            st.success("Binary image data successfully received (PNG).")

            # A. GET BOUNDS FROM METADATA API (Step 1 of 2)
            metadata_url = f"{METADATA_URL}/{RUN_ID}/{file_name}"
            st.info(f"Requesting bounds from: {metadata_url}")
            
            metadata_response = requests.get(metadata_url)
            
            if metadata_response.status_code == 200:
                metadata = metadata_response.json()
                bounds = metadata.get('bounds')
                
                st.success(f"Bounds retrieved: {bounds}")
                
                # B. VISUALIZATION (Step 2 of 2)
                
                # 1. Display the PNG image directly in Streamlit (from bytes)
                st.image(response.content)
                
                # 2. Add to the PyDeck Map using the original DATA_URL
                raster_layer = pdk.Layer(
                    "BitmapLayer",
                    image=full_url, # Use the original data URL as the image source
                    bounds=bounds,  # <-- USE THE RETRIEVED BOUNDS HERE!
                    opacity=0.7
                )

                # Set initial view to center on the bounds
                center_lon = (bounds[0] + bounds[2]) / 2 
                center_lat = (bounds[1] + bounds[3]) / 2
                
                view_state = pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=10, 
                    pitch=0
                )
                
                st.pydeck_chart(pdk.Deck(
                    map_style='light', # Use the token-free light style
                    initial_view_state=view_state,
                    layers=[raster_layer],
                ))
            
            else:
                st.error(f"Failed to retrieve metadata. Status: {metadata_response.status_code}")

    else:
        st.error(f"API Request Failed (Status Code: {response.status_code}). Error: {response.text}")