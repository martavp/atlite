# %% [markdown]
# # Creating a Cutout with ERA5

# %% [markdown]
# In this example we download ERA5 data on-demand for a cutout we want to create.
# (atlite does also work with other datasources, but ERA5 is the easiest one to get started.)
# 
# This only works if you have in before
# 
# * Installed the Copernicus Climate Data Store `cdsapi` package
# * Registered and setup your CDS API key as described [on their website here](https://cds.climate.copernicus.eu/api-how-to)

# %% [markdown]
# Import the package first:

# %%
import sys #to use files in git_repos folder
sys.path.insert(0,'../../atlite')
import atlite

# %% [markdown]
# We implement notifications in `atlite` using loggers from the `logging` library.
# 
# We recommend you always launch a logger to get information on what is going on.
# For debugging, you can use the more verbose `level=logging.DEBUG`:

# %%
import logging
logging.basicConfig(level=logging.INFO)


# %% [markdown]
# ## Defining the Cutout extent
# 
# > This will not yet trigger any major operations.
# 
# A cutout is the basis for any of your work and calculations.
# 
# The `cutout` is created in the directory and file specified by the relative `path`
# If a cutout at the given location already exists, then this command will simply load the cutout again.
# If the cutout does not yet exist, it will specify the new to-be-created cutout.
# > **Note** `ERA5`, Before the data can be downloaded it has to be processed by CDS servers, this might take a while depending on the ammout of data requested. 
# You can check the status of your request [here](https://cds.climate.copernicus.eu/cdsapp#!/yourrequests).

# %%
cutout = atlite.Cutout(
    path="cutouts/era5/western-europe-2011-01.nc",
    module="era5",
    x=slice(-13.6913, 1.7712),
    y=slice(49.9096, 60.8479),
    time="2011-01",
)

# %% [markdown]
# For creating the cutout, you need to specify
# 
# * The dataset to create the cutout with (`era5`)
# * The time period it covers
# * The longitude `x` and latitude `y` it stretches
# 
# 
# Here we went with the `ERA5` dataset from ECMWF
# 
# ```
# module="era5"
# ```
# 
# Here we decided to provide the `time` period of the cutout as a string, because it is only a month.
# You could have also specify it as a time range
# 
# ```
# slice("2011-01","2011-01")
# ```
# 
# The regional bounds (space the cutout stretches) where specified by the
# ```
# x=slice(-13.6913, 1.7712) # Longitude
# y=slice(49.9096, 60.8479) # Latitude
# ```
# 
# and describe a rectangle's edges.
# In this case we drew a rectangle containing some parts of the atlantic ocean,
# the Republic of Ireland and the UK.

# %% [markdown]
# ## Preparing the Cutout
# 
# If the cutout does not yet exist or has some features which are not yet included, we have to tell atlite to go ahead and do so.
# 
# No matter which dataset you use, this is where all the work actually happens.
# This can be fast or take some or a lot of time and resources, among others depending on
# your computer ressources and (for downloading e.g. ERA5 data) your internet connection.

# %%
cutout.prepare()

# %% [markdown]
# The `cutout.prepare()` function takes a list of features which should be prepared. When this is not specified, all available features are build. 
# 
# After, the execution all downloaded data is stored at `cutout.path`. Per default it is not loaded into memory, but into [dask](https://dask.org/) arrays. This keeps the memory consumption extremely low.  
# 
# The data is accessible in `cutout.data` which is an `xarray.Dataset`. 
# Querying the cutout gives us some basic information on which data is contained
# in it.

# %%
cutout.data

# %% [markdown]
# We can again breakdown which data array belongs to which feature.

# %%
cutout.prepared_features

# %% [markdown]
# If you have matplotlib installed, you can directly use the 
# plotting functionality from `xarray` to plot features from
# the cutout's data.
# 
# > **Warning**
# >  This will trigger `xarray` to load all the corresponding data from disk into memory!
# 
# 

# %% [markdown]
# Now that your cutout is created and prepared, you can call conversion functions as `cutout.pv` or `cutout.wind`. Note that this requires a bit more information, like what kind of pv panels to use, where do they stand etc. Please have a look at the other examples to get a picture of application cases.
cf_pv = cutout.pv(
    panel="CSi",
    orientation={"slope": 30.0, "azimuth": 180.0},
    shapes=cutout.grid,
    tracking=None,
    per_unit=True,
)

# Now you can plot all the converted solar generation values

# %%
cf_pv.plot()
# %%
# Or select one grid cell and plot the timeseries
plt.plot(cf_pv.data[:,0])
# %%
