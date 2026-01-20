import streamlit as st
import requests
import geopandas as gpd
import leafmap.foliumap as leafmap
import json
from io import StringIO
import folium

# --- Configuration ---
API_BASE_URL = 'https://latdn3bjub.execute-api.eu-north-1.amazonaws.com/default'
RASTER_EXTENSIONS = ('.tif', '.png')
VECTOR_EXTENSIONS = ('.geojson', '.gpkg', '.shp')


# --- Session State Initialization ---
# We use session_state to keep track of layers the user has "loaded"
if 'layers' not in st.session_state:
    st.session_state['layers'] = []

# --- Sidebar: File Selection ---
st.sidebar.title("Geospatial Data Visualiser", text_alignment="center")
st.sidebar.divider()
st.sidebar.header("AWS File Explorer")

def add_to_map(run_id, filename):
    """Fetch data and add it to the session state layer list"""
    full_url = f"{API_BASE_URL}/api/get-data/{run_id}/{filename}"
    
    with st.spinner(f"Loading {filename}..."):
        response = requests.get(full_url)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            # --- Handle Vector Data ---
            if 'application/json' in content_type or filename.endswith(('.geojson', '.gpkg', '.shp')):
                try:
                    geo_data_dict = response.json()
                    geojson_str = json.dumps(geo_data_dict)
                    gdf = gpd.read_file(StringIO(geojson_str))
                    gdf = gdf.to_crs(epsg=4326)
                    
                    # Store in session state
                    st.session_state['layers'].append({
                        "type": "vector",
                        "name": f"{run_id}/{filename}",
                        "data": gdf
                    })
                    st.sidebar.success(f"Added {filename}")
                except Exception as e:
                    st.sidebar.error(f"Vector error: {e}")

            # --- Handle Raster Data ---
            elif 'image/png' in content_type or filename.endswith('.png'):
                metadata_url = f"{API_BASE_URL}/api/metadata/{run_id}/{filename}"
                meta_res = requests.get(metadata_url)
                
                image = response.content
                if meta_res.status_code == 200:
                    bounds = meta_res.json().get('bounds') # [min_lon, min_lat, max_lon, max_lat]
                    # Leaflet needs [[min_lat, min_lon], [max_lat, max_lon]]
                    leaf_bounds = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
                    
                    st.session_state['layers'].append({
                        "type": "raster",
                        "name": f"{run_id}/{filename}",
                        "url": full_url,
                        "bounds": leaf_bounds,
                        "image_data": image
                    })

                    st.sidebar.success(f"Added {filename}")
                else:
                    st.sidebar.error("Could not fetch raster metadata for bounds.")
        else:
            st.sidebar.error(f"Failed to fetch file: {response.status_code}")

# 1. Fetch the file structure for the sidebar
try:
    fs_response = requests.get(f"{API_BASE_URL}/api/get-file-structure/data_storage")
    if fs_response.status_code == 200:
        file_tree = fs_response.json()
        
        for run_id, files in file_tree.items():
            with st.sidebar.expander(f"📁 Run: {run_id}"):
                for f in files:
                    col1, col2 = st.columns([3, 1])
                    col1.text(f)
                    # Logic: Only show the "+" button if it's a map-compatible file
                    is_vector = f.lower().endswith(VECTOR_EXTENSIONS)
                    is_raster = f.lower().endswith(RASTER_EXTENSIONS)

                    if is_vector or is_raster:
                        if col2.button("➕", key=f"add_{run_id}_{f}"):
                            add_to_map(run_id, f)
                    else:
                        col2.write("")
    else:
        st.sidebar.error("Failed to load file structure.")
except Exception as e:
    st.sidebar.error(f"Connection error: {e}")


# Sidebar for opacity control
global_opacity = st.sidebar.slider("Layer Opacity", 0.0, 1.0, 1.0, 0.05)

st.sidebar.divider()

# Button to clear the map
if st.sidebar.button("🗑️ Clear All Layers"):
    st.session_state['layers'] = []
    st.rerun()

# --- Map Rendering ---
# Create the base map
m = leafmap.Map(
    draw_control=False,
    measure_control=False,
    fullscreen_control=True
)
m.add_basemap("HYBRID", show=False) # Add a high-res basemap

# Add the layers from session state
for layer in st.session_state['layers']:
    if layer['type'] == 'vector':
        m.add_gdf(
            layer['data'], 
            layer_name=layer['name'],
            zoom_to_layer=True,
            info_mode='on_click',
            opacity=global_opacity,
        )
    elif layer['type'] == 'raster':
        # Using the direct Folium ImageOverlay for better stability with PNGs
        m.fit_bounds(layer['bounds'])
        img_overlay = folium.raster_layers.ImageOverlay(
            name=layer['name'],
            image=layer['url'],
            bounds=layer['bounds'],
            opacity=global_opacity,
            interactive=True,
            cross_origin=False,
            zindex=1
        )
        img_overlay.add_to(m)

# Add the Layer Control (the toggle UI)
m.add_layer_control()

# Display the map in the main area
m.to_streamlit(height=500)

# --- Metadata/Details Section ---
if st.session_state['layers']:
    with st.expander("Layer Details & Dataframes"):
        for i, layer in enumerate(st.session_state['layers']):
            st.write(f"**Layer {i+1}: {layer['name']}** ({layer['type']})")
            if layer['type'] == 'vector':
                st.dataframe(layer['data'])
            elif layer['type'] == 'raster':
                st.image(layer['image_data'])