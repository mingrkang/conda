# General purpose libraries.
import pandas as pd
import os
import numpy as np

# Geospatial libraries.
import geopandas as gpd
#import rasterio
#from rasterio.plot import show
import folium
import shapely

# Streamlit libraries
import streamlit as st
from streamlit_folium import st_folium

# For optimization
import cvxpy as cp
import networkx as nx
from scipy.spatial import distance


## Streamlit front end settings

st.set_page_config(page_title="Optimization Viz Test", layout="wide")
st.title("Optimization Viz Test")

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

    # Public schools (candidate sites)
    Public_Schools = gpd.read_file(os.path.join(data_path, "Public_Schools_WakeCounty.geojson"))

    return Census_Blocks, Voting_Precincts, Polling_Places, Public_Schools

Census_Blocks, Voting_Precincts, Polling_Places, Public_Schools = read_data(loadCensusBlocks=True)

# Convert all geoPandas objects to ESPG:3857 (flat) projection
Census_Blocks = Census_Blocks.to_crs(3857)
Voting_Precincts = Voting_Precincts.to_crs(3857)
Polling_Places = Polling_Places.to_crs(3857)
Public_Schools = Public_Schools.to_crs(3857)

# ## Processing attribute data
# CB_VP_merge = Census_Blocks.merge(Voting_Precincts, on='prec_id')[['BLOCKCE20','prec_id','total_reg','g20201103_voted_all','geometry_x','geometry_y']]
# #VP_lookup = CB_VP_merge.groupby('prec_id')[['total_reg','g20201103_voted_all']].sum().reset_index()
# VP_lookup = CB_VP_merge.groupby('prec_id')[['BLOCKCE20','total_reg','g20201103_voted_all']].agg({'BLOCKCE20':'size','total_reg':'sum','g20201103_voted_all':'sum'}).reset_index()

# ## Add precinct select box to sidebar
# VP_select = st.sidebar.selectbox('Select Voting Precinct', VP_lookup['prec_id'],index = None)
# #print(VP_select)
# if VP_select is not None:
#     VP_select_gdf = Voting_Precincts[Voting_Precincts['prec_id']==VP_select]  #GeoDataFrame for selected voting precinct
#     CB_select_gdf = Census_Blocks[Census_Blocks['prec_id']==VP_select]  # GeoDataFrame for Census Blocks in selected voting precinct
#     PP_select_gdf = Polling_Places[Polling_Places['USER_preci']=="PRECINCT {0}".format(VP_select)]  # GeoDataFrame for Polling Place assigned to selected voting precinct
#     PP_name = PP_select_gdf['USER_pol_1'].values[0]
#     PP_city = PP_select_gdf['USER_city'].values[0]
#     CB_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'BLOCKCE20'].values[0]
#     reg_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'total_reg'].values[0]
#     v2020_count = VP_lookup.loc[VP_lookup['prec_id']==VP_select,'g20201103_voted_all'].values[0]
#     st.sidebar.caption('Census Blocks assigned to Voting Precinct {0}:'.format(VP_select))
#     with st.sidebar:
#         VP_info = st.dataframe(
#             CB_VP_merge.loc[CB_VP_merge['prec_id']==VP_select,['BLOCKCE20','total_reg','g20201103_voted_all']].sort_values(by='total_reg', ascending=False),
#             column_config={
#                 "BLOCKCE20": "Block ID",
#                 "total_reg": "Registered",
#                 "g20201103_voted_all": "Voted in 2020"
#             },
#             hide_index=True)
#     st.sidebar.caption("Polling Place in 2020: {0}, {1}".format(PP_name,PP_city))
#     st.sidebar.caption("Total Census Blocks assigned: {0}".format(CB_count))
#     st.sidebar.caption("Total registered voters: {0}".format(reg_count))
#     st.sidebar.caption("Total who voted in 2020: {0}".format(v2020_count))


# Pulling Census block data for selected precinct(s)
PP = Polling_Places.assign(prec_id = Polling_Places['USER_preci'].str.replace(r'PRECINCT ',''))
selected_PPs = PP[PP['prec_id'].str.contains("01-06|01-07")]
PP_CB_merge = PP.merge(Census_Blocks, on='prec_id',how='left')[['GEOID20','prec_id','total_reg','g20201103_voted_all']]
PP_CB_merge = PP_CB_merge[PP_CB_merge['prec_id'].str.contains("01-06|01-07")].dropna()
selected_blocks = Census_Blocks[Census_Blocks['prec_id'].str.contains("01-06|01-07")]

# Pulling public schools (potential voting sites) for selected precincts
selected_schools = Public_Schools[Public_Schools['prec_id'].str.contains("01-06|01-07")]

# No. of registered voters in each Census block
block_voters = np.column_stack((selected_blocks.total_reg,selected_blocks.GEOID20))

# Coordinates for voting sites (including schools) and Census Blocks
sites = np.column_stack((selected_PPs.geometry.x,selected_PPs.geometry.y))
sites = np.row_stack((sites,np.column_stack((selected_schools.geometry.x,selected_schools.geometry.y))))
#sites = np.column_stack((sites.geometry.x,sites.geometry.y))
blocks = np.column_stack((selected_blocks.centroid.x, selected_blocks.centroid.y))

# Site operating costs and budget - assume same site numbers as 2020 election
site_costs = np.ones(len(sites))
site_budget = 3

# Voting site capacities - guestimate using voter turnout in the 2020 election
PP_lookup = PP_CB_merge.groupby('prec_id')[['GEOID20','total_reg','g20201103_voted_all']].agg({'GEOID20':'size','total_reg':'sum','g20201103_voted_all':'sum'}).reset_index()
#capacities = np.column_stack((PP_lookup['g20201103_voted_all'],PP_lookup['prec_id']))
capacities = np.ones(len(sites)) * 2000

# Distance matrix
d = distance.cdist(np.float64(blocks),np.float64(sites),'euclidean')

# Voting probability (turnout rate) as a function of distance to voting site
def prob_fun(dist):
    return 1-dist/np.max(d)         # simple linear function for toy example. To substitute with estimates from research studies.
#p = {1:1,2:0.75,3:0.5,4:0.25,5:0}  #voting probabilities.  Values should be decreasing with distance.
w = 1  # weight parameter (1 gives equal weight to operating costs vs. voter costs)

n, m = d.shape  #number of Census blocks, voting sites

## Decision variables
X = cp.Variable(m, boolean=True)
Y = cp.Variable((n,m), boolean=True)  #rows=blocks, cols=sites
Z = cp.Variable((n,m), boolean=True)  # helper variables to eliminate non-convexity in objective function

## Constraints
e_i = np.ones((n,1))  # column of ones across blocks
e_j = np.ones((m,1))  # column of ones across voting sites 

constraints = [site_costs.T @ X <= site_budget,
               Y.T @ block_voters[:,0] <= capacities,
               Y @ e_j == e_i]

## Solve cost minimization problem
objective = 0
for i in range(n):
    for j in range(m):
#        objective += X[j] * Y[i][j] * p[d[i][j]] * v[i]   # This formulation of the objective function is non-convex so it won't work with CVXPY.  Need to linearize.
#        objective += Z[i][j] * p[d[i][j]] * v[i]
        objective += Z[i][j] * prob_fun(d[i][j]) * block_voters[i,0]
        constraints.append(Z[i][j] <= X[j])                 # Constraints to linearize non-convexity involving product of two binary variables.
        constraints.append(Z[i][j] <= Y[i][j])
        constraints.append(Z[i][j] >= X[j] + Y[i][j] - 1)
        constraints.append(Y[i][j] <= X[j])  # Adding constraint that no census blocks can be assigned to an inactive voting site
objective = site_costs.T @ X - w * objective
prob = cp.Problem(cp.Minimize(objective), constraints)
prob.solve()
#prob.solve(solver='GLPK_MI')
print("Status:", prob.status)
print("Optimal value:", prob.value)
print("Voting sites used:", X.value)
print("Voter assignments:\n", Y.value)


## Building map using geopandas.explore and folium

selected_precincts = Voting_Precincts[Voting_Precincts['prec_id'].str.contains("01-06|01-07")]

combined_map = selected_precincts.explore(
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

# Add blocks for voting site 0
inds = np.ma.make_mask(Y.value[:,0])
blocks_0 = selected_blocks.loc[inds,['GEOID20','prec_id','g20201103_reg_all','geometry']]
blocks_0.explore(
    m=combined_map,  # Pass the previous map object
    color="brown",  # Use black color for borders.
#    column="g20201103_reg_all",  # Make choropleth based on "total_reg" column.
#    cmap = "afmhot_r", #color scheme
    # Styling instructions. We fill the wards with lightgrey color (when hovering over them),
    # and change the opacity of different elements.
    style_kwds=dict(
        fill=True, opacity=0.0, fillOpacity=0.5, interactive=True
    ),
    tiles="OpenStreetMap",  # Use Open Street Map background tiles.
#    tiles="CartoDB positron",
    tooltip=["GEOID20"],  # Do not show tooltip when hovering on wards.
    popup=["GEOID20", "prec_id","g20201103_reg_all"],  # Show the name of the ward on click.
    # Do not show the column label "ward_name" in the popup.
#    popup_kwds=dict(labels=False),
    smooth_factor=0,  # Prevent smoothing of the polygons edges.
    name="blocks_0",  # Name of the layer in the map.
)

# Add blocks for voting site 2
inds = np.ma.make_mask(Y.value[:,2])
blocks_2 = selected_blocks.loc[inds,['GEOID20','prec_id','g20201103_reg_all','geometry']]
blocks_2.explore(
    m=combined_map,  # Pass the previous map object
    color="red",  # Use black color for borders.
#    column="g20201103_reg_all",  # Make choropleth based on "total_reg" column.
#    cmap = "afmhot_r", #color scheme
    # Styling instructions. We fill the wards with lightgrey color (when hovering over them),
    # and change the opacity of different elements.
    style_kwds=dict(
        fill=True, opacity=0.0, fillOpacity=0.5, interactive=True
    ),
    tiles="OpenStreetMap",  # Use Open Street Map background tiles.
#    tiles="CartoDB positron",
    tooltip=["GEOID20"],  # Do not show tooltip when hovering on wards.
    popup=["GEOID20", "prec_id","g20201103_reg_all"],  # Show the name of the ward on click.
    # Do not show the column label "ward_name" in the popup.
#    popup_kwds=dict(labels=False),
    smooth_factor=0,  # Prevent smoothing of the polygons edges.
    name="blocks_2",  # Name of the layer in the map.
)

# Add blocks for voting site 6
inds = np.ma.make_mask(Y.value[:,6])
blocks_6 = selected_blocks.loc[inds,['GEOID20','prec_id','g20201103_reg_all','geometry']]
blocks_6.explore(
    m=combined_map,  # Pass the previous map object
    color="orange",  # Use black color for borders.
#    column="g20201103_reg_all",  # Make choropleth based on "total_reg" column.
#    cmap = "afmhot_r", #color scheme
    # Styling instructions. We fill the wards with lightgrey color (when hovering over them),
    # and change the opacity of different elements.
    style_kwds=dict(
        fill=True, opacity=0.0, fillOpacity=0.5, interactive=True
    ),
    tiles="OpenStreetMap",  # Use Open Street Map background tiles.
#    tiles="CartoDB positron",
    tooltip=["GEOID20"],  # Do not show tooltip when hovering on wards.
    popup=["GEOID20", "prec_id","g20201103_reg_all"],  # Show the name of the ward on click.
    # Do not show the column label "ward_name" in the popup.
#    popup_kwds=dict(labels=False),
    smooth_factor=0,  # Prevent smoothing of the polygons edges.
    name="blocks_6",  # Name of the layer in the map.
)


# Add Polling Places as third layer
selected_PPs.explore(
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

# Add schools
selected_schools.explore(
    m=combined_map,  # Pass the previous map object.
    color="purple",
#    column="USER_count",  # Make choropleth based on "category" column.
    tooltip=["school_nam"],  # Show values in tooltip (on hover)
    # Do not show column label in the tooltip.
    tooltip_kwds=dict(labels=False),
    # Show the selected values in popup (on click).
#    popup=["USER_count", "USER_pol_1", "USER_preci"],
#    cmap="gnuplot2",  # Use "gnuplot2" matplotlib color scheme.
    marker_kwds=dict(radius=5),  # Size of the points.
    # Styling instructions. We draw small black circles around our points,
    # and change the opacity of different elements.
    style_kwds=dict(color="black", weight=1, fill=True, opacity=0.5, fillOpacity=1),
    name="Schools",  # Name of the layer in the map.
)

# Adding markers to voting sites assigned by the model
selected_sites = pd.concat([gpd.GeoSeries(selected_schools.iloc[3,:]['geometry']),selected_PPs.iloc[[0,2]]['geometry']],ignore_index=True)
folium.GeoJson(
    selected_sites,
    marker=folium.Marker(icon=folium.Icon(icon='star'))
).add_to(combined_map)

# Use the folium library (which Geopandas is based on for interactive mapping) to add layer control
folium.LayerControl().add_to(combined_map)
    

# Load map
st_map = st_folium(combined_map, width=1000)

