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
from folium.plugins import Draw

# Voronoi and Zonal statistics libraries
#from rasterstats import zonal_stats

# Streamlit libraries
import streamlit as st
from streamlit_folium import st_folium


## Streamlit front end settings

st.set_page_config(page_title="Ming's Streamlit Test App", layout="wide")
st.title("Ming's Streamlit Test App")

## Loading data

data_path = os.path.join(os.getcwd(),"data")
#data_path = "C:\\Users\\Kang Family\Desktop\\OMSA\\CSE 6242\\project\\repo\\CSE6242_DVA_group_project\\data"
#print(data_path)

@st.cache_data
def read_data(loadCensusBlocks=False):
    # Census Block layer
    if loadCensusBlocks:
        Census_Blocks = gpd.read_file(
            os.path.join(data_path, "Census_Block_Stats_with_Precinct_WakeCounty.geojson")
        )
    else:
        Census_Blocks = None
    # Voting precinct layer
    Voting_Precincts = gpd.read_file(
        os.path.join(data_path, "Voting_Precincts_WakeCounty.geojson")
    )    

    # Polling place layer
    Polling_Places = gpd.read_file(os.path.join(data_path, "Polling_Places_WakeCounty.geojson"))

    return Census_Blocks, Voting_Precincts, Polling_Places

Census_Blocks, Voting_Precincts, Polling_Places = read_data(loadCensusBlocks=True)

## Processing attribute data
CB_VP_merge = Census_Blocks.merge(Voting_Precincts, on='prec_id')[['BLOCKCE20','prec_id','total_reg','g20201103_voted_all','geometry_x','geometry_y']]
#VP_lookup = CB_VP_merge.groupby('prec_id')[['total_reg','g20201103_voted_all']].sum().reset_index()
VP_lookup = CB_VP_merge.groupby('prec_id')[['BLOCKCE20','total_reg','g20201103_voted_all']].agg({'BLOCKCE20':'size','total_reg':'sum','g20201103_voted_all':'sum'}).reset_index()

## Add precinct select box to sidebar
VP_select = st.sidebar.selectbox('Select Voting Precinct', VP_lookup['prec_id'],index = None)
#print(VP_select)
if VP_select is not None:
    VP_select_gdf = Voting_Precincts[Voting_Precincts['prec_id']==VP_select]  #GeoDataFrame for selected voting precinct
    CB_select_gdf = Census_Blocks[Census_Blocks['prec_id']==VP_select]  # GeoDataFrame for Census Blocks in selected voting precinct
    PP_select_gdf = Polling_Places[Polling_Places['USER_preci']=="PRECINCT {0}".format(VP_select)]  # GeoDataFrame for Polling Place assigned to selected voting precinct
    PP_name = PP_select_gdf['USER_pol_1'].values[0]
    PP_city = PP_select_gdf['USER_city'].values[0]
    CB_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'BLOCKCE20'].values[0]
    reg_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'total_reg'].values[0]
    v2020_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'g20201103_voted_all'].values[0]
    st.sidebar.caption('Census Blocks assigned to Voting Precinct {0}:'.format(VP_select))
    with st.sidebar:
        VP_info = st.dataframe(
            CB_VP_merge.loc[CB_VP_merge['prec_id']==VP_select,['BLOCKCE20','total_reg','g20201103_voted_all']].sort_values(by='total_reg', ascending=False),
            column_config={
                "BLOCKCE20": "Block ID",
                "total_reg": "Registered",
                "g20201103_voted_all": "Voted in 2020"
            },
            hide_index=True)
    st.sidebar.caption("Polling Place in 2020: {0}, {1}".format(PP_name,PP_city))
    st.sidebar.caption("Total Census Blocks assigned: {0}".format(CB_count))
    st.sidebar.caption("Total registered voters: {0}".format(reg_count))
    st.sidebar.caption("Total who voted in 2020: {0}".format(v2020_count))

## Function to grab data based on bounding box drawn on map
def get_data_in_bbox(bbox, gdf):
    lat_min, lat_max, lon_min, lon_max = (bbox[0], bbox[2], bbox[1], bbox[3])  #lat_min, lat_max, lon_min, lon_max
    return gdf[(gdf['geometry'].x >= lon_min) & (gdf['geometry'].x <= lon_max) & (gdf['geometry'].y >= lat_min) & (gdf['geometry'].y <= lat_max)]


## Building map using geopandas.explore and folium

combined_map = folium.Map()
Draw(export=True).add_to(combined_map)

# Initializing bounding box selector
session_keys = list(st.session_state.keys())

START_BOUNDS = '''
{'_southWest': {'lat': 35.31064272673245, 'lng': -79.29656982421876}, '_northEast': {'lat': 36.09127994838079, 'lng': -77.92327880859376}}
'''

try:
    first_bounds = st.session_state[session_keys[0]]['bounds']
except Exception as e:
    first_bounds = START_BOUNDS

try:
    south = first_bounds['_southWest']['lat']
except Exception as e:
    south = 35.5
try:
    west = first_bounds['_southWest']['lng']
except Exception as e:
    west = -78.5
try:
    north = first_bounds['_northEast']['lat']
except Exception as e:
    north = -36
try:
    east = first_bounds['_northEast']['lng']
except Exception as e:
    east = -77

bbox = [south, west, north, east]
print(bbox)
PP_bbox_gdf = get_data_in_bbox(bbox,Polling_Places)

loadCensusBlocks=False
# explore() is a geopandas method to create interactive maps.
# we assign it to the variable 'combined_map', to add more map layers after.
combined_map = Voting_Precincts.explore(
    m = combined_map,
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
if loadCensusBlocks:
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


# Add selected precinct overlay
if VP_select is not None:
    # Voting Precinct
    VP_select_gdf.explore(
        m=combined_map,
        color="yellow",
        tooltip=False,
        smooth_factor=0,
        name="selected_precinct",  # Name of the layer in the map.
    )
    # Census Blocks in selected Voting Precinct
    CB_select_gdf.explore(
        m=combined_map,  # Pass the previous map object
        color="black",  # Use black color for borders.
        column="total_reg",  # Make choropleth based on "total_reg" column.
        cmap = "afmhot_r", #color scheme
        # Styling instructions. We fill the wards with lightgrey color (when hovering over them),
        # and change the opacity of different elements.
        style_kwds=dict(
            fill=True, opacity=0.0, fillOpacity=0.5, interactive=True
        ),
#        tiles="OpenStreetMap",  # Use Open Street Map background tiles.
    #    tiles="CartoDB positron",
        tooltip=False,  # Do not show tooltip when hovering on wards.
        popup=["BLOCKCE20", "prec_id","total_reg","g20201103_voted_all"],
        # Do not show the column label "ward_name" in the popup.
    #    popup_kwds=dict(labels=False),
        smooth_factor=0,  # Prevent smoothing of the polygons edges.
        name="Census_Blocks",  # Name of the layer in the map.
    )

# combined_map.add_gdf(
#     gdf=selected_gdf,
#     layer_name='selected',
#     zoom_to_layer=True,
#     info_mode=None,
#     style={'color': 'yellow', 'fill': None, 'weight': 2}
#  )

## Add bounding box selector for Polling Places
fg = folium.FeatureGroup(name="PP_bbox")

for data_point in PP_bbox_gdf.itertuples():
    folium.CircleMarker( 
        location=(data_point[-1].y,data_point[-1].x),  
        radius=4,  
        color='cornflowerblue', 
        fill=True, 
        fill_opacity=1, 
        opacity=1, 
    ).add_to(combined_map) 
# PP_bbox_gdf.explore(
#     m=combined_map,  # Pass the previous map object.
#     marker_kwds=dict(radius=10),  # Size of the points.
#     style_kwds=dict(color="orange", weight=1, fill=True, opacity=1, fillOpacity=1),
#     name="PP_bbox_selected",  # Name of the layer in the map.
# )

# Use the folium library (which Geopandas is based on for interactive mapping) to add layer control
folium.LayerControl().add_to(combined_map)
    

# Load map
st_map = st_folium(combined_map, feature_group_to_add = fg, width=1000, key = "st_map")

