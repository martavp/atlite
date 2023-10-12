# -*- coding: utf-8 -*-
"""
Modified from: https://atlite.readthedocs.io/en/latest/examples/plotting_with_atlite.html 

"""

#import os
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import geopandas as gpd
import pandas as pd
#from pandas.plotting import register_matplotlib_converters
#register_matplotlib_converters()

import cartopy.crs as ccrs
from cartopy.crs import PlateCarree as plate
import cartopy.io.shapereader as shpreader

#import xarray as xr
import atlite

import logging
import warnings

warnings.simplefilter("ignore")
logging.captureWarnings(False)
logging.basicConfig(level=logging.INFO)


#%%
#Define country and shapes
shpfilename = shpreader.natural_earth(resolution="10m", 
                                      category="cultural", 
                                      name="admin_0_countries")

reader = shpreader.Reader(shpfilename)


#country='Denmark'
Denmark = gpd.GeoSeries({r.attributes["NAME_EN"]: r.geometry for r in reader.records()},
    crs={"init": "epsg:4326"},).reindex(["Denmark"])

#%%
# Define and download cutout
cutout = atlite.Cutout(
    path="Denmark-2020-06", module="era5", bounds=Denmark.unary_union.bounds, 
    time="2020-06")
cutout.prepare()

#%% (not mandatory) Plotting cutout on Globe
projection = ccrs.Orthographic(10, 55)
                                      
cells = cutout.grid
df = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
country_bound = gpd.GeoSeries(cells.unary_union)


fig, ax = plt.subplots(subplot_kw={"projection": projection}, figsize=(6, 6))
df.plot(ax=ax, transform=plate())
country_bound.plot(ax=ax, edgecolor="firebrick", facecolor="None", transform=plate())
fig.tight_layout()
plt.savefig('figures/global_view.jpg', 
            dpi=300, bbox_inches='tight')
#%% (not mandatory) Plotting weather data from cutout
fig = plt.figure(figsize=(12, 7))
gs = GridSpec(3, 3, figure=fig)

ax = fig.add_subplot(gs[:, 0:2], projection=projection)
plot_grid_dict = dict(
    alpha=0.1,
    edgecolor="k",
    zorder=4,
    aspect="equal",
    facecolor="None",
    transform=plate(),
)
Denmark.plot(ax=ax, zorder=1, transform=plate())
cells.plot(ax=ax, **plot_grid_dict)
country_bound.plot(ax=ax, edgecolor="firebrick", facecolor="None", transform=plate())
ax.outline_patch.set_edgecolor("white")

ax1 = fig.add_subplot(gs[1, 2])
cutout.data.wnd100m.mean(["x", "y"]).plot(ax=ax1, color='orange')
ax1.set_frame_on(False)
ax1.xaxis.set_visible(False)
ax1.set_ylabel("Wind velocity \n 100 m (m/s)")

ax2 = fig.add_subplot(gs[0, 2], sharex=ax1)
cutout.data.influx_direct.mean(["x", "y"]).plot(ax=ax2, color='green')
ax2.set_frame_on(False)
ax2.xaxis.set_visible(False)
ax2.set_ylabel("Solar irradiation \n (W/m2)")

ax3 = fig.add_subplot(gs[2, 2], sharex=ax1)
cutout.data.runoff.mean(["x", "y"]).plot(ax=ax3, color='blue')
times=cutout.data.runoff.mean(["x", "y"])["time"]
ax3.set_frame_on(False)
ax3.set_xlabel(None)
ax3.set_ylabel("Runoff")
ax3.set_xticks([times.values[0],
                times.values[250],
                times.values[500],
                times.values[719],])
fig.tight_layout()

plt.savefig('figures/weather_time_series.jpg', 
            dpi=300, bbox_inches='tight')

#%% (not mandatory) Plotting 
#annual capacity factors for wind and solar PV
cap_factors_wind = cutout.wind(turbine="Vestas_V112_3MW", capacity_factor=True)

fig, ax = plt.subplots(subplot_kw={"projection": projection}, 
                       figsize=(11, 4))
#cap_factors.name = "Capacity Factor Wind"
cap_factors_wind.plot(ax=ax, transform=plate(), alpha=0.8, cmap='winter_r')

cells.plot(ax=ax, **plot_grid_dict)
ax.outline_patch.set_edgecolor("white")
fig.tight_layout();

plt.savefig('figures/capacity_factor_wind.jpg', 
            dpi=300, bbox_inches='tight')

correction_factor=0.5
cap_factors_solar = correction_factor*cutout.pv(panel="CSi", 
                        orientation={"slope": 30.0, "azimuth": 180.0},
                        capacity_factor=True)

fig, ax = plt.subplots(subplot_kw={"projection": projection}, 
                        figsize=(11, 4))
#cap_factors.name = "Capacity Factor Solar PV"

cap_factors_solar.plot(ax=ax, transform=plate(), alpha=0.7, cmap='autumn')
cells.plot(ax=ax, **plot_grid_dict)
ax.outline_patch.set_edgecolor("white")
fig.tight_layout();

plt.savefig('figures/capacity_factor_solar.jpg', 
            dpi=300, bbox_inches='tight')

#%%
# Create aggregated time-series for wind and solar
cf_exponent=2
layout_wind=cap_factors_wind**cf_exponent
total_capacity_layout=layout_wind.values.sum()
agg_cf_wind = (1/total_capacity_layout)*cutout.wind(turbine="Vestas_V112_3MW", 
                                                    layout=layout_wind).to_pandas()
fig, ax = plt.subplots(1, figsize=(12, 8))
agg_cf_wind.plot.area(ax=ax)

ax.text(0.5, 0.9, 
        'mean CF = ' + str(round(agg_cf_wind.values.mean(),2)), 
        fontsize=20,
        horizontalalignment='center',
        verticalalignment='center', 
        transform=ax.transAxes)

fig.tight_layout()
plt.savefig('figures/agg_cf_wind.jpg', 
            dpi=300, bbox_inches='tight')


#%%
cf_exponent=2
layout_solar=cap_factors_solar**cf_exponent
total_capacity_layout=layout_solar.values.sum()
agg_cf_solar = (1/total_capacity_layout)*cutout.pv(panel="CSi", 
                                                       orientation={"slope": 30.0, "azimuth": 180.0},
                             layout=layout_solar,).to_pandas()

fig, ax = plt.subplots(1, figsize=(12, 8))
agg_cf_solar.plot.area(ax=ax, color='orange')

ax.text(0.5, 0.9, 
        'mean CF = ' + str(round(agg_cf_solar.values.mean(),2)), 
        fontsize=20,
        horizontalalignment='center',
        verticalalignment='center', 
        transform=ax.transAxes)

fig.tight_layout()
plt.savefig('figures/agg_cf_solar.jpg', 
            dpi=300, bbox_inches='tight')


