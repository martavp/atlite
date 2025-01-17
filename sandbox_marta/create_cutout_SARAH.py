# %% [markdown]
# # Creating a Cutout with the SARAH-2 dataset

# %% [markdown]
# This walkthrough describes the process of creating a cutout using the [SARAH-2 dataset by EUMETSAT](https://wui.cmsaf.eu/safira/action/viewDoiDetails?acronym=SARAH_V002_01).
# 
# The SARAH-2 dataset contains extensive information on solar radiation variables, like surface incoming direct radiation (SID) or surface incoming shortwave radiation (SIS).
# It serves as an addition to the ERA5 dataset and as such requires the `cdsapi` to be setup properly.
# 
# > **Recommendation**
# >
# > This is a reduced version for cutout creation. Creating cutouts with ERA-5 is simpler and explained in more details.
# > We therefore recommend you have a look at [this example first](https://atlite.readthedocs.io/en/latest/examples/create_cutout.html).
# 
# > **Note**:
# >
# > For creating a cutout from this dataset, you need to download large files and your computers memory needs to be able to handle these as well.

# %% [markdown]
# ## Downloading the data set

# %% [markdown]
# To download the dataset, head to the EUMETSTATs website (the link points to the current 2.1 edition)
# 
# https://wui.cmsaf.eu/safira/action/viewDoiDetails?acronym=SARAH_V002_01 
# 
# On the bottom, select the products you want to include in the cutout, i.e. for us:
# 
# | variable | time span | time resolution | 
# | --- | --- | --- |
# | Surface incoming direct radiation (SID) | 2013 | Instantaneous |
# | Surface incoming shortwave radiation (SIS) | 2013 | Instantaneous |
# 
# * Add each product to your cart and register with the website.
# * Follow the instructions to activate your account, confirm your order and wait for the download to be ready.
# * You will be notified by email with the download instructions.
# * Download the ordered files of your order into a directory, e.g. `sarah-2`.
# * Extract the `tar` files (e.g. for linux systems `tar -xvf *` or with `7zip` for windows) into the same folder
# 
# You are now ready to create cutouts using the SARAH-2 dataset.

# %% [markdown]
# ## Specifying the cutout

# %% [markdown]
# Import the package and set recommended logging settings:

# %%
import logging
logging.basicConfig(level=logging.INFO)

import sys #to use files in git_repos folder
sys.path.insert(0,'../../atlite')
import atlite

# %%
start_date = "2025-01-01"
end_date = "2025-01-02"
cutout = atlite.Cutout(
    path="cutouts/sarah/western-europe-2025-01.nc",
    module=["sarah", "era5"],
    sarah_dir="sarah_v3", #"/cutouts/sarah_v3",
    x=slice(-13.6913, 1.7712),
    y=slice(49.9096, 60.8479),
   # time="2013-01",
    time=slice(start_date, end_date),
    chunks={"time": 100},
)

# %% [markdown]
# Let's see what the available features that is the available weather data variables are.

# %%
cutout.available_features.to_frame()

# %% [markdown]
# ## Preparing the Cutout
# 
# No matter which dataset you use, this is where all the work actually happens.
# This can be fast or take some or a lot of time and resources, among others depending on
# your computer ressources (especially memory for SARAH-3).

# %%
cutout.prepare()

# %% [markdown]
# Querying the cutout gives us basic information on which data is contained and can already be used.

# %% [markdown]
# ## Inspecting the Cutout

# %%
cutout  # basic information

# %%
cutout.data.attrs  # cutout meta data

# %%
cutout.prepared_features  # included weather variables

# %%
cutout.data  # access to underlying xarray data


