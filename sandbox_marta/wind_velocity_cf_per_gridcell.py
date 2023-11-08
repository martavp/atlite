#!/usr/bin/env python
# coding: utf-8

""" 
This script retrieve hourly wind velocity data per grid cell and
calculate hourly wind capacity per grid cell using a cutout for Europe 2013.

Using cutout data downloaded from 
 https://zenodo.org/record/6382570 

"""

import sys #to use files in git_repos folder
sys.path.insert(0,'../../atlite')

import atlite
import numpy as np
import matplotlib.pyplot as plt

# load cutout data. file need to be downloaded manually
cutout=atlite.Cutout("cutouts/europe-2013-era5.nc")


# Retrieving the wind velocity at 100m
wnd100m=cutout.data['wnd100m'].values
# The array includes wind velocity data at 100m height for the latitudes, longitudes
# and timesteps in 
lon=cutout.data['lon'].values
lat=cutout.data['lat'].values
time=cutout.data['time'].values
#saving the array
np.save('wnd100m.npy', wnd100m)

#%%
# Wind power CF per gridcell map
CF_wind = cutout.wind('Vestas_V112_3MW', 
                      capacity_factor=True,
                      capacity_factor_timeseries=True)
#%%
# The array includes wind capacity fators for the same latitudes, longitudes
# and timesteps
#saving the array
np.save('CF_wind.npy', CF_wind)
#%%
# wind velocity time series for the first grid cell
plt.plot(wnd100m[:,0,0])

#capacity factor time series for the first grid cell
plt.plot(CF_wind[:,0,0])





