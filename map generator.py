import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from io import BytesIO
import matplotlib.ticker as mticker
import json
from shapely.geometry import Polygon
import warnings

# Suppress centroid warning
warnings.filterwarnings("ignore", category=UserWarning, message="Geometry is in a geographic CRS.*")

st.set_page_config(layout="centered")
st.title("Study Area Map Generator (With PNG Export)")

# Define shapefile paths and corresponding name fields
level_options = {
    "Country": {
        "path": "data/shp files/ken_admbnda_adm0_iebc_20191031.shp",
        "field": "ADM0_EN"
    },
    "County": {
        "path": "data/shp files/ken_admbnda_adm1_iebc_20191031.shp",
        "field": "ADM1_EN"
    },
    "Sub-County": {
        "path": "data/shp files/ken_admbnda_adm2_iebc_20191031.shp",
        "field": "ADM2_EN"
    }
}

# Optional: Polygon coordinate input
st.subheader("Optional: Paste Custom Polygon Coordinates (Overrides Dropdown Selection)")

coords_input = st.text_area("Enter Coordinates as GeoJSON-style List (e.g., [[lon, lat], [lon, lat], ...])")

if coords_input.strip():
    try:
        coords = json.loads(coords_input)
        if not isinstance(coords, list) or not all(isinstance(p, list) and len(p) == 2 for p in coords):
            raise ValueError("Invalid coordinate format.")
        flipped_coords = [(y, x) for x, y in coords]
        custom_poly = gpd.GeoDataFrame(geometry=[Polygon(flipped_coords)], crs="EPSG:4326")
        study_area = custom_poly

        # Let user define a name
        user_polygon_name = st.text_input("Enter the Name of This Area (e.g., Miyuga Site, Forest Block 3)", "Custom Area")
        selected_area = user_polygon_name

    except Exception as e:
        st.error(f"Invalid input: {e}")
        st.stop()
else:
    # User selects level
    level = st.selectbox("Select Level of Study Area", list(level_options.keys()))
    shapefile_info = level_options[level]

    # Load selected shapefile
    try:
        gdf = gpd.read_file(shapefile_info["path"])
    except Exception as e:
        st.error(f"Error loading shapefile: {e}")
        st.stop()

    name_field = shapefile_info["field"]

    # Extract area names
    try:
        area_names = sorted(gdf[name_field].unique())
    except KeyError:
        st.error(f"Field '{name_field}' not found in shapefile.")
        st.write("Available columns:", list(gdf.columns))
        st.stop()

    # User selects the specific study area
    selected_area = st.selectbox(f"Select {level}", area_names)
    study_area = gdf[gdf[name_field] == selected_area]
    study_area = study_area.to_crs(epsg=4326)

# Plot map
fig, ax = plt.subplots(figsize=(10, 10))
study_area.plot(ax=ax, edgecolor='black', facecolor='lightgreen', alpha=0.7)

# Add label inside the polygon (centered)
centroid = study_area.geometry.centroid.iloc[0]
ax.text(centroid.x, centroid.y, selected_area,
        horizontalalignment='center', verticalalignment='center',
        fontsize=12, weight='bold', color='darkgreen')

# Add legend
legend_patch = Patch(facecolor='lightgreen', edgecolor='black', label='Study Area')
ax.legend(handles=[legend_patch], loc='upper right')

# Add north arrow
x, y, arrow_length = 0.1, 0.9, 0.05
ax.annotate('', xy=(x, y + arrow_length), xytext=(x, y),
            arrowprops=dict(facecolor='black', width=5, headwidth=15),
            xycoords='axes fraction')
ax.text(x, y + arrow_length + 0.02, 'N', transform=ax.transAxes,
        ha='center', va='bottom', fontsize=14, weight='bold')

# Format coordinates with N/S/E/W
def decimal_deg_formatter(val, pos, axis='x'):
    direction = 'E' if axis == 'x' and val >= 0 else 'W' if axis == 'x' else 'N' if val >= 0 else 'S'
    return f"{abs(val):.1f}°{direction}"

ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda val, pos: decimal_deg_formatter(val, pos, 'x')))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda val, pos: decimal_deg_formatter(val, pos, 'y')))

# Add labels, grid, title, credit
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.tick_params(axis='both', labelsize=10, direction='out')
ax.grid(True)
ax.set_title("Fig. 1 Study Area Map", fontsize=16, weight='bold')
fig.text(0.5, 0.02, "Credit: Basil Okoth Kaudo", ha='center', fontsize=10, style='italic')

# Display map
st.pyplot(fig)

# PNG export
buf = BytesIO()
fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
st.download_button("📥 Download Map as PNG",
                   data=buf.getvalue(),
                   file_name=f"study_area_map_{selected_area}.png",
                   mime="image/png")
