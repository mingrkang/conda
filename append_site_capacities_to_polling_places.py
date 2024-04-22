import json
import pandas as pd
import geopandas as gpd
import pickle
import os
import numpy as np


data_path = os.path.join(os.getcwd(),"data")

## Load data
# Census Blocks attribute data
Census_Blocks = pd.read_csv(
    os.path.join(data_path, "NC_l2_2022stats_2020block.csv")
)

# Voting precincts
Voting_Precincts = gpd.read_file(
    os.path.join(data_path, "Voting_Precincts.geojson")
)    

# Polling places
Polling_Places = gpd.read_file(
    os.path.join(data_path, "Polling_Places.geojson")
)

