# SPDX-FileCopyrightText: Contributors to atlite <https://github.com/pypsa/atlite>
#
# SPDX-License-Identifier: MIT
"""
Module containing specific operations for creating cutouts from the KNMI-LENTIS dataset.
https://doi.org/10.5194/gmd-16-4581-2023

"""

import glob
import logging
import os
import warnings
from contextlib import nullcontext
from functools import partial

import numpy as np
import pandas as pd
import xarray as xr
from dask.array import arctan2, sqrt
from rasterio.warp import Resampling

from atlite.gis import regrid
from atlite.pv.irradiation import DiffuseHorizontalIrrad
from atlite.pv.solar_position import SolarPosition

logger = logging.getLogger(__name__)

# Physical constants for hypsometric height calculation
_R_D = 287.05   # Specific gas constant for dry air, J kg-1 K-1
_G   = 9.80665  # Standard acceleration of gravity, m s-2


# Model, CRS and resolution Settings
crs = 4326
dx = 360 / 512  # ~0.703°
dy = 180 / 256  # ~0.703°
dt = "3h"
features = {
    "height": ["height"],
    "influx": ["influx_toa",
               "influx_direct",
               "influx_diffuse",
               "albedo",
               "solar_altitude",
               "solar_azimuth"],
    "wind": ["wnd10m",
             "wnd100m",
             "wnd_shear_exp",
             "wnd_azimuth"],
    "temperature": ["temperature", 
                    "soil temperature"],
    "runoff": ["runoff"],
}
static_features = {"height"}


def get_filenames(lentis_dir, coords, varname="rsds", freq="3hr"):
    
    """
    Get all files in directory `lentis_dir` relevant for coordinates `coords`.

    Scans the lentis directory for NetCDF files of the given variable and
    frequency whose time ranges overlap with the cutout time span.

    Parameters
    ----------
    lentis_dir : str
    coords : atlite.Cutout.coords
    varname : str, optional
        CMIP6 variable name (default ``"rsds"``).
    freq : str, optional
        CMIP6 frequency string used in filenames, e.g. ``"3hr"`` or ``"day"``
        (default ``"3hr"``).

    Returns
    -------
    pd.Series of file paths indexed by file start date, filtered to files
    covering the cutout time span.
    """

    pattern = os.path.join(lentis_dir, "**", f"{varname}_{freq}_*.nc")
    files = pd.Series(glob.glob(pattern, recursive=True))
    assert not files.empty, (
        f"No files found at {pattern}. Make sure "
        f"lentis_dir points to the correct directory!"
    )
    # CMIP6 filenames end in _YYYYMM[DD[HHMM]]-YYYYMM[DD[HHMM]].nc; extract start/end date.
    # Monthly (Lmon) files use YYYYMM (6 digits); sub-daily use YYYYMMDD or YYYYMMDDhhmm.
    starts = pd.to_datetime(
        files.str.extract(r"_(\d{6})\d*-\d+\.nc$", expand=False),
        format="%Y%m",
    )
    ends = pd.to_datetime(
        files.str.extract(r"_\d+-(\d{6})\d*\.nc$", expand=False),
        format="%Y%m",
    )
    files.index = starts

    start = coords["time"].to_index()[0].floor("D")
    end = coords["time"].to_index()[-1].floor("D")

    mask = (files.index <= end) & (ends.values >= start)
    filtered = files.loc[mask].sort_index()

    if filtered.empty:
        logger.error(
            f"Files in {lentis_dir} do not cover the time span: {start} to {end}"
        )

    return filtered


def interpolate(ds, dim="time"):
    """
    Interpolate NaNs in a dataset along a chunked dimension.

    This function is similar to xr.Dataset.interpolate_na but can be
    used for interpolating along a chunked dimension (default 'time').
    """

    def _interpolate1d(y):
        nan = np.isnan(y)
        if nan.all() or not nan.any():
            return y

        def x(z):
            return z.nonzero()[0]

        y = np.array(y)
        y[nan] = np.interp(x(nan), x(~nan), y[~nan])
        return y

    def _interpolate(a):
        return a.map_blocks(
            partial(np.apply_along_axis, _interpolate1d, -1), dtype=a.dtype
        )

    data_vars = ds.data_vars.values() if isinstance(ds, xr.Dataset) else (ds,)
    dtypes = {da.dtype for da in data_vars}
    assert len(dtypes) == 1, "interpolate only supports datasets with homogeneous dtype"

    return xr.apply_ufunc(
        _interpolate,
        ds,
        input_core_dims=[[dim]],
        output_core_dims=[[dim]],
        output_dtypes=[dtypes.pop()],
        output_sizes={dim: len(ds.indexes[dim])},
        dask="allowed",
        keep_attrs=True,
    )


def as_slice(bounds, pad=True):
    """
    Convert coordinate bounds to slice and pad by 0.01.
    """
    if not isinstance(bounds, slice):
        bounds = bounds + (-0.01, 0.01)
        bounds = slice(*bounds)
    return bounds


def crop_and_rename(ds, cutout):

    """
    LENTIS uses 0–360 longitude, normalize to -180/180.
    Crop to cutout extent
    Rename 'longitude' and 'latitude' columns to 'x' and 'y.

    """

    ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180)
    ds = ds.sortby("lon")
    ds = ds.sel(lon=as_slice(cutout.extent[:2]), lat=as_slice(cutout.extent[2:]))
    if (cutout.dx != dx) or (cutout.dy != dy):
        ds = regrid(ds, cutout.coords["lon"], cutout.coords["lat"], resampling=Resampling.average)

    ds = ds.assign_coords(x=ds.coords["lon"], y=ds.coords["lat"])
    ds = ds.swap_dims({"lon": "x", "lat": "y"})
    return ds.drop_vars(["lon", "lat"])


def get_data_height(cutout, lentis_dir, **_):
    """
    Load LENTIS static orography (orog_fx_*.nc) as a 2-D height field.

    Parameters
    ----------
    cutout : atlite.Cutout
    lentis_dir : str
        Root directory of the LENTIS dataset.

    Returns
    -------
    xarray.Dataset
        Dataset with variable ``height`` (metres) on (y, x) coordinates.
    """
    coords = cutout.coords
    chunks = cutout.chunks

    _orog_pattern = os.path.join(lentis_dir, "**", "orog_fx_*.nc")
    _orog_files = glob.glob(_orog_pattern, recursive=True)
    if not _orog_files:
        raise FileNotFoundError(
            f"No orography file (orog_fx_*.nc) found in {lentis_dir}."
        )

    ds = xr.open_dataset(_orog_files[0], chunks=chunks)[["orog"]]

    ds = crop_and_rename(ds, cutout)
    ds = ds.rename({"orog": "height"})

    return ds.assign_coords(cutout.coords)


def get_data_wind(cutout, lentis_dir, parallel=False, lock=None, **_):
    """
    Load LENTIS 3-hourly surface wind data and reformat to match the given cutout.

    Uses 3-hourly ``uas``/``vas`` (10 m surface wind components) to derive
    ``wnd10m``, ``wnd100m``, and ``wnd_azimuth``.
    ``wnd_shear_exp`` is set to a constant 1/7 everywhere.
   
    ``wnd_shear_exp`` is computed using the power law applied to wind speeds
    at the 1000 hPa (approx. 100m) and 850 hPa  (approx. 1500m) levels, with heights derived from the
    hypsometric equation. Requires daily ``ua``, ``va``, ``ta``, 3-hourly
    ``ps``, ``tas``, and static ``orog`` in ``lentis_dir``.

    Parameters
    ----------
    cutout : atlite.Cutout
    lentis_dir : str
        Root directory of the LENTIS dataset.
    parallel : bool, optional
        Whether to open files in parallel. Default is False.

    Returns
    -------
    xarray.Dataset
    """
    coords = cutout.coords
    chunks = cutout.chunks
    open_kw = dict(chunks=chunks, parallel=parallel)
    _ctx = lock if lock is not None else nullcontext()

    with _ctx:
        ds_uas = xr.open_mfdataset(
            get_filenames(lentis_dir, coords, varname="uas", freq="3hr"),
            combine="by_coords", **open_kw,
        )[["uas"]]
    with _ctx:
        ds_vas = xr.open_mfdataset(
            get_filenames(lentis_dir, coords, varname="vas", freq="3hr"),
            combine="by_coords", **open_kw,
        )[["vas"]]
    ds = xr.merge([ds_uas, ds_vas])
    ds = crop_and_rename(ds, cutout)
    ds = ds.interp({"time": coords["time"]}, method="linear",
                   kwargs={"assume_sorted": True})

    ds["wnd10m"] = sqrt(ds["uas"] ** 2 + ds["vas"] ** 2).assign_attrs(
        units="m s-1", long_name="10 metre wind speed"
    )
   
    azimuth = arctan2(ds["uas"], ds["vas"])
    ds["wnd_azimuth"] = azimuth.where(azimuth >= 0, azimuth + 2 * np.pi)

    # --- wnd_shear_exp: power-law exponent from 1000 hPa and 850 hPa levels ---
    with _ctx:
        ds_plev = xr.merge([
            xr.open_mfdataset(
                get_filenames(lentis_dir, coords, varname="ua", freq="day"),
                combine="by_coords", **open_kw,
            )[["ua"]],
            xr.open_mfdataset(
                get_filenames(lentis_dir, coords, varname="va", freq="day"),
                combine="by_coords", **open_kw,
            )[["va"]],
            xr.open_mfdataset(
                get_filenames(lentis_dir, coords, varname="ta", freq="day"),
                combine="by_coords", **open_kw,
            )[["ta"]],
        ]).sel(plev=[100000.0, 85000.0])
    with _ctx:
        ds_surf = xr.merge([
            xr.open_mfdataset(
                get_filenames(lentis_dir, coords, varname="tas", freq="3hr"),
                combine="by_coords", **open_kw,
            )[["tas"]],
            xr.open_mfdataset(
                get_filenames(lentis_dir, coords, varname="ps", freq="3hr"),
                combine="by_coords", **open_kw,
            )[["ps"]],
        ])
    _orog_pattern = os.path.join(lentis_dir, "**", "orog_fx_*.nc")
    _orog_files = glob.glob(_orog_pattern, recursive=True)
    if not _orog_files:
        raise FileNotFoundError(f"No orog_fx_*.nc found in {lentis_dir}")
    ds_orog = xr.open_dataset(_orog_files[0], chunks=chunks)[["orog"]]

    # Select pressure levels before crop_and_rename: regrid can't handle the
    # extra plev dimension (rasterio only accepts 2D/3D arrays).
    ds_plev_1000 = crop_and_rename(ds_plev.sel(plev=100000.0, drop=True), cutout)
    ds_plev_850  = crop_and_rename(ds_plev.sel(plev=85000.0,  drop=True), cutout)
    ds_surf = crop_and_rename(ds_surf, cutout)
    ds_orog = crop_and_rename(ds_orog, cutout)

    # Broadcast daily pressure-level data → 3-hourly cutout timestamps
    ds_plev_1000 = ds_plev_1000.assign_coords(time=ds_plev_1000.time.dt.floor("D"))
    ds_plev_850  = ds_plev_850.assign_coords(time=ds_plev_850.time.dt.floor("D"))
    ds_plev_1000 = ds_plev_1000.reindex(time=coords["time"], method="ffill")
    ds_plev_850  = ds_plev_850.reindex(time=coords["time"], method="ffill")

    # Align 3-hourly surface fields to cutout timestamps
    ds_surf = ds_surf.reindex(time=coords["time"])

    ta_1000 = ds_plev_1000["ta"]
    ta_850  = ds_plev_850["ta"]

    T_mean_sfc_1000 = (ds_surf["tas"] + ta_1000) / 2.0
    T_mean_1000_850 = (ta_1000 + ta_850) / 2.0

    # Height of pressure levels above sea level via hypsometric equation
    h_1000_amsl = (
        ds_orog["orog"]
        + (_R_D * T_mean_sfc_1000 / _G) * np.log(ds_surf["ps"] / 100000.0)
    )
    h_850_amsl = (
        h_1000_amsl
        + (_R_D * T_mean_1000_850 / _G) * np.log(100000.0 / 85000.0)
    )

    # Height above ground level (orography cancels)
    h_1000_agl = (h_1000_amsl - ds_orog["orog"]).clip(min=11.0)
    h_850_agl  = (h_850_amsl  - ds_orog["orog"]).clip(min=h_1000_agl + 1.0)

    wnd_1000 = sqrt(ds_plev_1000["ua"] ** 2 + ds_plev_1000["va"] ** 2)
    wnd_850  = sqrt(ds_plev_850["ua"]  ** 2 + ds_plev_850["va"]  ** 2)

    ds["wnd_shear_exp"] = (
        np.log(wnd_1000 / wnd_850) / np.log(h_1000_agl / h_850_agl)
    ).clip(min=0).assign_attrs(
        units="", long_name="wind shear exponent (1000–850 hPa power law)"
    )

    ds["wnd100m"] = (ds["wnd10m"] * (100 / 10) ** ds["wnd_shear_exp"]).assign_attrs(
        units="m s-1", long_name="100 metre wind speed (power-law extrapolation)"
    )

    return ds.drop_vars(["uas", "vas", "height"], errors="ignore")


def get_data_temperature(cutout, lentis_dir, parallel=False, lock=None, **_):
    """
    Load LENTIS temperature data and reformat to match the given cutout.

    Returns ``temperature`` (3-hourly ``tas``) and ``soil temperature``
    (monthly ``tsl`` at the deepest depth level (2m), interpolated to cutout timestamps).
    """
    coords = cutout.coords
    chunks = cutout.chunks
    open_kwargs = dict(chunks=chunks, parallel=parallel)
    _ctx = lock if lock is not None else nullcontext()

    files = get_filenames(lentis_dir, coords, varname="tas", freq="3hr")
    with _ctx:
        ds = xr.open_mfdataset(files, combine="by_coords", **open_kwargs)[["tas"]]
    ds = crop_and_rename(ds, cutout)
    ds = ds.interp({"time": coords["time"]}, method="linear", kwargs={"assume_sorted": True})
    ds = ds.rename({"tas": "temperature"})
    ds = ds.drop_vars(["height"], errors="ignore")

    # Load monthly soil temperature (tsl), select deepest level (~2 m, analogous to ERA5 stl4)
    tsl_files = get_filenames(lentis_dir, coords, varname="tsl", freq="Lmon")
    with _ctx:
        ds_tsl = xr.open_mfdataset(tsl_files, combine="by_coords", **open_kwargs)[["tsl"]]
    ds_tsl = ds_tsl.isel(depth=3, drop=True)
    ds_tsl = crop_and_rename(ds_tsl, cutout)
    ds_tsl = ds_tsl.interp(
        {"time": coords["time"]}, method="linear", kwargs={"assume_sorted": True}
    )
    ds_tsl = ds_tsl.rename({"tsl": "soil temperature"})
    ds_tsl = ds_tsl.drop_vars(["height"], errors="ignore")

    return xr.merge([ds, ds_tsl])


def get_data_runoff(cutout, lentis_dir, parallel=False, lock=None, **_):
    """
    Load LENTIS runoff data and reformat to match the given cutout.

    Converts 3-hourly ``mrro`` (kg m⁻² s⁻¹) to metres per 3h timestep and
    clips to non-negative values.
    """
    coords = cutout.coords
    chunks = cutout.chunks
    open_kwargs = dict(chunks=chunks, parallel=parallel)
    _ctx = lock if lock is not None else nullcontext()

    files = get_filenames(lentis_dir, coords, varname="mrro", freq="3hr")
    with _ctx:
        ds = xr.open_mfdataset(files, combine="by_coords", **open_kwargs)[["mrro"]]
    ds = crop_and_rename(ds, cutout)
    ds = ds.interp({"time": coords["time"]}, method="linear", kwargs={"assume_sorted": True})
    ds["mrro"] = ds["mrro"] * 3 * 3600 / 1000  # kg m⁻² s⁻¹ → m per 3h timestep
    ds["mrro"] = ds["mrro"].clip(min=0.0)
    ds = ds.rename({"mrro": "runoff"})
    return ds.drop_vars(["height"], errors="ignore")


def get_data_influx(cutout, lentis_dir, parallel=False, lock=None, **_):
    """
    Load LENTIS solar radiation data and reformat to match the given cutout.

    ``influx_toa`` is calculated from solar geometry;

    `influx_direct` and `influx_diffuse` are derived from the interpolated
    ``rsds`` using the Reindl 1990 clearsky-index decomposition model.

    ``rsus`` (surface upwelling shortwave radiation) is used solely to compute albedo 
    """
    coords = cutout.coords
    chunks = cutout.chunks
    open_kwargs = dict(chunks=chunks, parallel=parallel)
    _ctx = lock if lock is not None else nullcontext()

    files = get_filenames(lentis_dir, coords, varname="rsds", freq="3hr")
    with _ctx:
        ds = xr.open_mfdataset(files, combine="by_coords", **open_kwargs)[["rsds"]]
    files_rsus = get_filenames(lentis_dir, coords, varname="rsus", freq="3hr")
    with _ctx:
        ds_rsus = xr.open_mfdataset(files_rsus, combine="by_coords", **open_kwargs)[["rsus"]]
    ds = xr.merge([ds, ds_rsus])

    ds = ds.assign_coords(lon=((ds.lon + 180) % 360) - 180)
    ds = ds.sortby("lon")
    ds = ds.sel(lon=as_slice(cutout.extent[:2]), lat=as_slice(cutout.extent[2:]))

    ds = interpolate(ds)

    if (cutout.dx != dx) or (cutout.dy != dy):
        ds = regrid(ds, coords["lon"], coords["lat"], resampling=Resampling.average)

    ds = ds.assign_coords(x=ds.coords["lon"], y=ds.coords["lat"])
    ds = ds.swap_dims({"lon": "x", "lat": "y"})
    ds = ds.drop_vars(["lon", "lat"])

    # Interpolate rsds to cutout timestamps. Since cutout timestamps (00:00, 03:00, ...)
    # are always equidistant between consecutive LENTIS midpoints (01:30, 04:30, ...),
    # linear interpolation gives the arithmetic mean of the two surrounding values.
    ds = ds.interp({"time": coords["time"]}, method="linear", kwargs={"assume_sorted": True})

    # SolarPosition needs lon/lat named coords; add them temporarily from x/y values.
    # Do not show DeprecationWarning from new SolarPosition calculation (#199)
    ds_sp = ds.assign_coords(lon=ds.coords["x"], lat=ds.coords["y"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        sp = SolarPosition(ds_sp, time_shift="0H")
    sp = sp.drop_vars(["lon", "lat"], errors="ignore")
    sp = sp.rename({v: f"solar_{v}" for v in sp.data_vars})
    ds = xr.merge([ds, sp])

    # Top-of-atmosphere horizontal irradiance from solar geometry
    I0 = 1367.0  # solar constant, W m-2
    doy = ds["time"].dt.dayofyear
    eccentricity = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0)
    ds["influx_toa"] = (
        (I0 * eccentricity * np.sin(ds["solar_altitude"]))
        .clip(min=0)
        .assign_attrs(long_name="Top-of-atmosphere horizontal irradiance", units="W m-2")
    )

    # Reindl 1990 direct/diffuse decomposition
    solar_position_reindl = ds[["solar_altitude"]].rename({"solar_altitude": "altitude"})
    influx = ds["rsds"].clip(min=0)
    diffuse = DiffuseHorizontalIrrad(
        ds, solar_position_reindl, clearsky_model="simple", influx=influx
    )
    direct = (influx - diffuse).clip(min=0)
    ds["influx_direct"] = direct.assign_attrs(
        long_name="Surface Direct Shortwave Flux (Reindl 1990)", units="W m-2"
    )
    ds["influx_diffuse"] = diffuse.assign_attrs(
        long_name="Surface Diffuse Shortwave Flux (Reindl 1990)", units="W m-2"
    )
    ds["albedo"] = (
        (ds["rsus"] / ds["rsds"].where(ds["rsds"] != 0))
        .fillna(0.0)
        .clip(max=1.0)
        .assign_attrs(units="(0 - 1)", long_name="Albedo")
    )
    ds = ds.drop_vars(["rsds", "rsus", "height"], errors="ignore")

    return ds



def get_data(
    cutout, feature, lock=None, **creation_parameters
):
    """
    Load stored LENTIS data and reformat to match the given cutout.

    Parameters
    ----------
    cutout : atlite.Cutout
    feature : str
        Name of the feature data to retrieve. Must be in
        `atlite.datasets.lentis.features`.
    **creation_parameters :
        Mandatory arguments are:
            * 'lentis_dir', str. Directory of the stored LENTIS data.
        Possible arguments are:
            * 'parallel', bool. Whether to load stored files in parallel
            mode. Default is False.

    Returns
    -------
    xarray.Dataset
        Dataset of dask arrays of the retrieved variables.

    """
    assert cutout.dt in ("3h", "3H"), (
        f"LENTIS data has 3-hourly resolution; cutout.dt must be '3h', got {cutout.dt!r}"
    )

    lentis_dir = creation_parameters["lentis_dir"]
    creation_parameters.setdefault("parallel", False)

    if feature == "height":
        return get_data_height(
            cutout,
            lentis_dir=lentis_dir,
        )

    if feature == "wind":
        return get_data_wind(
            cutout,
            lentis_dir=lentis_dir,
            parallel=creation_parameters["parallel"],
            lock=lock,
        )

    if feature == "temperature":
        return get_data_temperature(
            cutout,
            lentis_dir=lentis_dir,
            parallel=creation_parameters["parallel"],
            lock=lock,
        )

    if feature == "runoff":
        return get_data_runoff(
            cutout,
            lentis_dir=lentis_dir,
            parallel=creation_parameters["parallel"],
            lock=lock,
        )

    return get_data_influx(
        cutout,
        lentis_dir=lentis_dir,
        parallel=creation_parameters["parallel"],
        lock=lock,
    )
