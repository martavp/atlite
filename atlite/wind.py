# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2016-2019 The Atlite Authors
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Functions for use in conjunction with wind data generation.
"""

import numpy as np
import re

import logging

logger = logging.getLogger(__name__)


def extrapolate_wind_speed(ds, model, to_height, from_height=None, from_height2=None):
    """Extrapolate the wind speed from a given height above ground to another.

    If ds already contains a key refering to wind speeds at the desired to_height,
    no conversion is done and the wind speeds are directly returned.

    Extrapolation of the wind speed follows the logarithmic law as desribed in [1].

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing the wind speed time-series at 'from_height' with key
        'wnd{height:d}m' and the surface orography with key 'roughness' at the
        geographic locations of the wind speeds.
    from_height : int
        (Optional)
        Height (m) from which the wind speeds are interpolated to 'to_height'.
        If not provided, the closest height to 'to_height' is selected.
    to_height : int|float
        Height (m) to which the wind speeds are extrapolated to.

    from_height2 : int
        (Optional)
        Second height (m) from which the wind speeds are interpolated to 'to_height'.
        If not provided, two closest heights to 'to_height' are selected from available wind speed heights.

    Returns
    -------
    da : xarray.DataArray
        DataArray containing the extrapolated wind speeds. Name of the DataArray
        is 'wnd{to_height:d}'.

    References
    ----------
    [1] Equation (2) in Andresen, G. et al (2015): 'Validation of Danish wind
    time series from a new global renewable energy atlas for energy system
    analysis'.

    [2] https://en.wikipedia.org/w/index.php?title=Roughness_length&oldid=862127433,
    Retrieved 2019-02-15.
    """
    # Fast lane
    to_name = "wnd{h:0d}m".format(h=int(to_height))
    if to_name in ds:
        return ds[to_name]

    if from_height is None:
        # Determine closest height to to_name
        heights = np.asarray([int(s[3:-1]) for s in ds if re.match(r"wnd\d+m", s)])

        if len(heights) == 0:
            raise AssertionError("Wind speed is not in dataset")

        # Checking if cutout contains wind speed at more than 1 height level
        if len(heights) > 1:
            possible_extrapolate_without_roughness=True
            from_height = heights[np.argmin(np.abs(heights - to_height))]
            heights = np.delete(heights, np.argmin(np.abs(heights - to_height)))
            from_height2 = heights[np.argmin(np.abs(heights - to_height))]      # Finding second closest height
        else: 
            possible_extrapolate_without_roughness=False
            from_height = heights[np.argmin(np.abs(heights - to_height))]

    if model == "interpolation" and possible_extrapolate_without_roughness:
        extrapolate_without_roughness = True
        print("Calculating wind speed at hub height using 2 wind speed datasets.")
    else:
        extrapolate_without_roughness = False
        print("Calculating wind speed at hub height using 1 wind speed dataset and surface roughness dataset.")

    # Wind speed interpolation with option to NOT use surface roughness: 
    if extrapolate_without_roughness==True: 
        from_name = "wnd{h:0d}m".format(h=int(from_height))
        from_name2 = "wnd{h:0d}m".format(h=int(from_height2))         # definition of second wind speed (for instance at 100m)

        wnd_spd = ds[from_name] * (to_height / from_height)**((1 / np.log(from_height)) * np.log(ds[from_name2] / ds[from_name]))

        wnd_spd.attrs.update(
            {
            "long name": "extrapolated {ht} m wind speed using logarithmic "
            "method with {hf} m and {hf2} m wind speed"
            "".format(ht=to_height, hf=from_height, hf2=from_height2),
            "units": "m s**-1",
            }
        )
    
    # Wind speed extrapolation for the standard case with 1 wind speed height
    else:
        from_name = "wnd{h:0d}m".format(h=int(from_height))
        from_name2 = None
        wnd_spd = ds[from_name] * (
            np.log(to_height / ds["roughness"]) / np.log(from_height / ds["roughness"])
        )
        wnd_spd.attrs.update(
            {
                "long name": "extrapolated {ht} m wind speed using logarithmic "
                "method with roughness and {hf} m wind speed"
                "".format(ht=to_height, hf=from_height),
                "units": "m s**-1",
            }
        )

    return wnd_spd.rename(to_name)