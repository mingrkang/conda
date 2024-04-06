# General purpose libraries.
import pandas as pd
import os
import numpy as np

# Geospatial libraries.
import geopandas as gpd
import rasterio
from rasterio.plot import show
import folium
import shapely

# Voronoi and Zonal statistics libraries
#from rasterstats import zonal_stats

# Streamlit libraries
import streamlit as st
from streamlit_folium import st_folium

#data_path = os.path.join(os.getcwd(),"data")
data_path = "C:\\Users\\Kang Family\Desktop\\OMSA\\CSE 6242\\project\\repo\\CSE6242_DVA_group_project\\data"
print(data_path)

# # Census Block layer
# Census_Blocks = gpd.read_file(
#     os.path.join(data_path, "Census_Block_Stats_with_Precinct_WakeCounty.geojson")
# )
# Voting precinct layer
Voting_Precincts = gpd.read_file(
    os.path.join(data_path, "Voting_Precincts_WakeCounty.geojson")
)    

# Polling place layer
Polling_Places = gpd.read_file(os.path.join(data_path, "Polling_Places_WakeCounty.geojson"))

# explore() is a geopandas method to create interactive maps.
# we assign it to the variable 'combined_map', to add more map layers after.
combined_map = Voting_Precincts.explore(
    color="blue",
#    column="enr_desc",  # Make choropleth based on "category" column.
    tooltip="enr_desc",  # Show "name" value in tooltip (on hover)
    # Do not show column label in the tooltip.
    tooltip_kwds=dict(labels=False),
    cmap="gnuplot2",  # Use "gnuplot2" matplotlib color scheme.
    style_kwds=dict(
        fill=True, opacity=1.0, fillOpacity=0.0, interactive=True
    ),
    smooth_factor=0,
    name="Voting_Precincts",  # Name of the layer in the map.
)

# Add Census Blocks as second layer
Census_Blocks.explore(
    m=combined_map,  # Pass the previous map object
    color="black",  # Use black color for borders.
    column="g20201103_reg_all",  # Make choropleth based on "total_reg" column.
    cmap = "afmhot_r", #color scheme
    # Styling instructions. We fill the wards with lightgrey color (when hovering over them),
    # and change the opacity of different elements.
    style_kwds=dict(
        fill=True, opacity=0.0, fillOpacity=0.5, interactive=True
    ),
    tiles="OpenStreetMap",  # Use Open Street Map background tiles.
#    tiles="CartoDB positron",
    tooltip=False,  # Do not show tooltip when hovering on wards.
    popup=["BLOCKCE20", "prec_id","g20201103_reg_all"],  # Show the name of the ward on click.
    # Do not show the column label "ward_name" in the popup.
#    popup_kwds=dict(labels=False),
    smooth_factor=0,  # Prevent smoothing of the polygons edges.
    name="Census_Blocks",  # Name of the layer in the map.
)

# Add Polling Places as third layer
Polling_Places.explore(
    m=combined_map,  # Pass the previous map object.
#    column="USER_count",  # Make choropleth based on "category" column.
    tooltip=["USER_pol_1","USER_preci"],  # Show values in tooltip (on hover)
    # Do not show column label in the tooltip.
    tooltip_kwds=dict(labels=False),
    # Show the selected values in popup (on click).
    popup=["USER_count", "USER_pol_1", "USER_preci"],
#    cmap="gnuplot2",  # Use "gnuplot2" matplotlib color scheme.
    marker_kwds=dict(radius=5),  # Size of the points.
    # Styling instructions. We draw small black circles around our points,
    # and change the opacity of different elements.
    style_kwds=dict(color="black", weight=1, fill=True, opacity=0.5, fillOpacity=0.8),
    name="Polling_Places",  # Name of the layer in the map.
)

# Use the folium library (which Geopandas is based on for interactive mapping) to add layer control
folium.LayerControl().add_to(combined_map)

st_map = st_folium(combined_map, width=1000)

