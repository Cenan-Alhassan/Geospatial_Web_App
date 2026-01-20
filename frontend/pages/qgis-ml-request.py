import streamlit as st
import json
import requests

st.set_page_config(layout="wide", page_title="SCP Processing Request")

# --- Configuration ---
# Default to localhost since your Flask app runs on port 5000
DEFAULT_API_URL = "http://127.0.0.1:5000/ml-request"

# --- Sidebar: Server Config ---
st.sidebar.title("Make a Classification Request")
st.sidebar.divider()

with st.sidebar:
    st.header("Server Config")
    api_url = st.text_input("QGIS ML Server URL", value=DEFAULT_API_URL)
    st.info("Ensure qgis-ml-server-flask.py is running. Note that only the owner of the server has access to this command.")

# --- Constants & Defaults ---
DEFAULT_PARAMS = {
    'BAND_INPUT_LAYERS': [
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B02.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B03.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B04.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B05.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B06.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B07.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B08.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B8A.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B11.tif',
        'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/processed-clipped/clipRT_T30UXC_A053745_20251006T110612_B12.tif'
    ],
    'TRAINING_INPUT_SCPX': r'C:\Users\User\OneDrive\Desktop\GIS-ML\london-lulc\london-lulc-macroclass-only-training.scpx',
    'TESTING_INPUT_SCPX': 'C:/Users/User/OneDrive/Desktop/GIS-ML/london-lulc/testing.gpkg',
    'USE_MACROCLASS': True,
    'MC_OR_CLASS_FIELD': 'macroclass_id',
    'NODATA': None,
    'NORMALIZATION': None,
    'ML_MODEL': 2, # Spectral Angle Mapping default
    'SINGLE_THRESHOLD': None,
    'SIGNATURE_THRESHOLD': False,
    'SAVE_SIGNATURE': False,
    'CALCULATE_CONFIDENCE': False,
    'MLP_LAYERS': '100',
    'MLP_MAX_ITER': 200,
    'MLP_ACTIVATION': 'relu',
    'MLP_APLHA': 0.01,
    'MLP_TRAIN_PORTION': 0.9,
    'MLP_BATCH_SIZE': 'auto',
    'MLP_LEARNING_RATE_INIT': 0.001,
    'CROSS_VALIDATION': False,
    'RF_TREES': 10,
    'RF_SPLIT': 2,
    'RF_MAX_FEATURES': '',
    'RF_ONE_VS_REST': False,
    'SVM_REGULARIZATION': 1,
    'SVM_KERNEL': 'rbf',
    'SVM_GAMMA': 'scale',
    'FIND_BEST_ESTIMATOR': None,
    'BALANCED_CLASS_WEIGHT': False,
    'CLASSIFIER_INPUT_RSMO': '',
    'RASTER_OUTPUT': 'TEMPORARY_OUTPUT',
    'CLASSIFICATION_FOLDER': r'C:\Users\User\OneDrive\Desktop\GIS-ML\london-lulc'
}

# --- Helper Mappings ---
ML_MODEL_OPTIONS = [
    'Minimum Distance', 'Maximum Likelihood', 'Spectral Angle Mapping',
    'Random Forest', 'Support Vector Machine', 'Multi-Layer Perceptron',
    'PyTorch Multi-Layer Perceptron'
]

NORM_OPTIONS = ['Z-Score', 'Linear Scaling']

st.markdown("Configure the `scp-classification.py` parameters and send to QGIS Server.")

with st.form("scp_request_form"):
    
    # --- SECTION 1: INPUTS ---
    st.subheader("1. Inputs & Outputs")
    
    # Band Layers
    default_bands_str = "\n".join(DEFAULT_PARAMS['BAND_INPUT_LAYERS'])
    bands_input = st.text_area("Input Band Layers (One path per line)", value=default_bands_str, height=200)
    
    col1, col2 = st.columns(2)
    with col1:
        training_input = st.text_input("Training Input (.scpx)", value=DEFAULT_PARAMS['TRAINING_INPUT_SCPX'])
        testing_input = st.text_input("Testing Input (Vector)", value=DEFAULT_PARAMS['TESTING_INPUT_SCPX'])
        classifier_input = st.text_input("Classifier Input (.rsmo) [Optional]", value=DEFAULT_PARAMS['CLASSIFIER_INPUT_RSMO'])
        
    with col2:
        output_folder = st.text_input("Classification Output Folder", value=DEFAULT_PARAMS['CLASSIFICATION_FOLDER'])
        raster_output = st.text_input("Raster Output Name", value=DEFAULT_PARAMS['RASTER_OUTPUT'])
        nodata_val = st.number_input("NoData Value (0 = None)", value=DEFAULT_PARAMS['NODATA'] if DEFAULT_PARAMS['NODATA'] is not None else 0.0)

    # --- SECTION 2: CONFIGURATION ---
    st.subheader("2. General Configuration")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        default_model_idx = DEFAULT_PARAMS['ML_MODEL']
        ml_model_idx = st.selectbox(
            "Algorithm", 
            options=range(len(ML_MODEL_OPTIONS)), 
            format_func=lambda x: ML_MODEL_OPTIONS[x],
            index=default_model_idx
        )
    
    with c2:
        norm_ui_options = ["None"] + NORM_OPTIONS
        norm_selection = st.selectbox("Input Normalization", options=norm_ui_options)

    with c3:
        mc_field = st.text_input("Class/Macroclass Field", value=DEFAULT_PARAMS['MC_OR_CLASS_FIELD'])

    # Boolean Toggles
    st.markdown("**Options**")
    b1, b2, b3, b4, b5 = st.columns(5)
    use_macro = b1.checkbox("Use Macroclass", value=DEFAULT_PARAMS['USE_MACROCLASS'])
    save_sig = b2.checkbox("Save Signature", value=DEFAULT_PARAMS['SAVE_SIGNATURE'])
    calc_conf = b3.checkbox("Calc Confidence", value=DEFAULT_PARAMS['CALCULATE_CONFIDENCE'])
    cross_val = b4.checkbox("Cross Validation", value=DEFAULT_PARAMS['CROSS_VALIDATION'])
    sig_thresh_bool = b5.checkbox("Signature Threshold", value=DEFAULT_PARAMS['SIGNATURE_THRESHOLD'])
    
    # --- SECTION 3: ALGORITHM SPECIFICS ---
    st.subheader("3. Algorithm Specifics")
    
    with st.expander("Threshold Methods (Min Dist, Max Like, SAM)", expanded=True):
        thresh_val = st.number_input("Single Threshold Value", value=0.0)

    with st.expander("Random Forest Settings"):
        rf_c1, rf_c2 = st.columns(2)
        rf_trees = rf_c1.number_input("Number of Trees", value=DEFAULT_PARAMS['RF_TREES'])
        rf_split = rf_c2.number_input("Min Samples Split", value=DEFAULT_PARAMS['RF_SPLIT'])
        rf_feats = st.text_input("Max Features", value=DEFAULT_PARAMS['RF_MAX_FEATURES'])
        rf_ovr = st.checkbox("One-Vs-Rest", value=DEFAULT_PARAMS['RF_ONE_VS_REST'])
        rf_balanced = st.checkbox("Balanced Class Weight", value=DEFAULT_PARAMS['BALANCED_CLASS_WEIGHT'])

    with st.expander("Support Vector Machine Settings"):
        svm_c1, svm_c2, svm_c3 = st.columns(3)
        svm_c = svm_c1.number_input("Regularization (C)", value=float(DEFAULT_PARAMS['SVM_REGULARIZATION']))
        svm_kernel = svm_c2.text_input("Kernel", value=DEFAULT_PARAMS['SVM_KERNEL'])
        svm_gamma = svm_c3.text_input("Gamma", value=DEFAULT_PARAMS['SVM_GAMMA'])

    with st.expander("Multi-Layer Perceptron Settings"):
        mlp_layers = st.text_input("Hidden Layers (comma sep)", value=DEFAULT_PARAMS['MLP_LAYERS'])
        mlp_c1, mlp_c2 = st.columns(2)
        mlp_iter = mlp_c1.number_input("Max Iterations", value=DEFAULT_PARAMS['MLP_MAX_ITER'])
        mlp_act = mlp_c2.text_input("Activation", value=DEFAULT_PARAMS['MLP_ACTIVATION'])
        mlp_alpha = st.number_input("Alpha", value=DEFAULT_PARAMS['MLP_APLHA'], format="%.4f")
        mlp_rate = st.number_input("Learning Rate Init", value=DEFAULT_PARAMS['MLP_LEARNING_RATE_INIT'], format="%.4f")

    # Submit
    submitted = st.form_submit_button("Run Classification")

if submitted:
    # --- 1. BUILD JSON PAYLOAD ---
    
    final_bands = [line.strip() for line in bands_input.split('\n') if line.strip()]
    if not final_bands:
        final_bands = DEFAULT_PARAMS['BAND_INPUT_LAYERS']

    final_norm = None
    if norm_selection == "Z-Score":
        final_norm = 0
    elif norm_selection == "Linear Scaling":
        final_norm = 1
    
    payload = {
        'BAND_INPUT_LAYERS': final_bands,
        'TRAINING_INPUT_SCPX': training_input if training_input else DEFAULT_PARAMS['TRAINING_INPUT_SCPX'],
        'TESTING_INPUT_SCPX': testing_input if testing_input else DEFAULT_PARAMS['TESTING_INPUT_SCPX'],
        'USE_MACROCLASS': use_macro,
        'MC_OR_CLASS_FIELD': mc_field if mc_field else DEFAULT_PARAMS['MC_OR_CLASS_FIELD'],
        'NODATA': nodata_val if nodata_val != 0 else None,
        'NORMALIZATION': final_norm,
        'ML_MODEL': ml_model_idx,
        'SINGLE_THRESHOLD': thresh_val if thresh_val != 0 else None,
        'SIGNATURE_THRESHOLD': sig_thresh_bool,
        'SAVE_SIGNATURE': save_sig,
        'CALCULATE_CONFIDENCE': calc_conf,
        
        # MLP
        'MLP_LAYERS': mlp_layers if mlp_layers else DEFAULT_PARAMS['MLP_LAYERS'],
        'MLP_MAX_ITER': int(mlp_iter),
        'MLP_ACTIVATION': mlp_act,
        'MLP_APLHA': mlp_alpha,
        'MLP_TRAIN_PORTION': DEFAULT_PARAMS['MLP_TRAIN_PORTION'],
        'MLP_BATCH_SIZE': DEFAULT_PARAMS['MLP_BATCH_SIZE'],
        'MLP_LEARNING_RATE_INIT': mlp_rate,
        
        # Cross Val
        'CROSS_VALIDATION': cross_val,
        
        # RF
        'RF_TREES': int(rf_trees),
        'RF_SPLIT': int(rf_split),
        'RF_MAX_FEATURES': rf_feats,
        'RF_ONE_VS_REST': rf_ovr,
        
        # SVM
        'SVM_REGULARIZATION': svm_c,
        'SVM_KERNEL': svm_kernel,
        'SVM_GAMMA': svm_gamma,
        
        'FIND_BEST_ESTIMATOR': DEFAULT_PARAMS['FIND_BEST_ESTIMATOR'],
        'BALANCED_CLASS_WEIGHT': rf_balanced,
        'CLASSIFIER_INPUT_RSMO': classifier_input,
        'RASTER_OUTPUT': raster_output,
        'CLASSIFICATION_FOLDER': output_folder
    }

    # --- 2. SEND TO SERVER ---
    st.info(f"Sending request to {api_url}...")
    
    try:
        with st.spinner("Processing in QGIS... this may take a while."):
            response = requests.post(api_url, json=payload, timeout=300) # 5 minute timeout
            
            if response.status_code == 200:
                data = response.json()
                st.success("Classification Successful!")
                
                # Display Results
                result_data = data.get("result", {})
                st.json(result_data)
                
                # Extract Output path if available
                if "RASTER_OUTPUT" in result_data:
                    st.write(f"Check AWS File Explorer for output raster")
                    
            else:
                st.error(f"Server Error: {response.status_code}")
                try:
                    st.json(response.json())
                except:
                    st.text(response.text)
                    
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the server. Is `qgis-ml-server-flask.py` running?")
    except requests.exceptions.Timeout:
        st.error("The request timed out. The classification might still be running in the background.")
    except Exception as e:
        st.error(f"An error occurred: {e}")