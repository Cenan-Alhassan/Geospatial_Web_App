import streamlit as st

# 1. Define the pages
# These link to your actual python files
map_page = st.Page("data-visualiser.py", title="Geospatial Visualiser", default=True)
ml_page = st.Page("pages/qgis-ml-request.py", title="Run Machine Learning")

# 2. Create the navigation menu
pg = st.navigation({
    "Pages": [map_page, ml_page]
})

# 3. SET PAGE CONFIG MUST BE IN THE MAIN SCRIPT
st.set_page_config(layout="wide", page_title="Geospatial ML App")

# 4. Run the navigation
pg.run()