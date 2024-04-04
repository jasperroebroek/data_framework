import shutil
from pathlib import Path

import numpy as np
import rasterio as rio
import rasterio.warp
import xarray as xr
from affine import Affine
from rasterio import CRS
from rasterio.dtypes import dtype_rev
from rasterio.enums import Resampling
from rioxarray.raster_array import _NODATA_DTYPE_MAP

from data_framework.paths import path_temp
from data_framework.types import Shape


def reproject(da: xr.DataArray, path: Path, src_crs: CRS, dst_crs: CRS, dst_transform: Affine, dst_shape: Shape,
              resampling: Resampling = Resampling.nearest, **reprojection_kwargs) -> None:
    """da is reprojected and stored in path"""
    if path.exists():
        return

    temp_path = path_temp / f"~{'_'.join(path.parts[1:])}"

    if da.ndim != 2:
        raise IndexError("Only 2D is supported")

    print(f"Reprojecting: da -> {path}")

    path.parent.mkdir(parents=True, exist_ok=True)

    dtype = reprojection_kwargs.pop('dtype', da.dtype)

    da_nodata = (
        _NODATA_DTYPE_MAP.get(dtype_rev[np.dtype(dtype).name])
        if da.rio.nodata is None
        else da.rio.nodata
    )

    dst_nodata = reprojection_kwargs.pop('nodata', da_nodata)

    compress = reprojection_kwargs.pop('compress', "DEFLATE")
    compress_level = reprojection_kwargs.pop('compress_level', 9 if compress == "DEFLATE" else None)

    profile = {
        'driver': 'GTiff',
        'height': dst_shape[0],
        'width': dst_shape[1],
        'dtype': dtype,
        'nodata': dst_nodata,
        'compress': compress,
        'zlevel': compress_level,
        'count': 1,
        'crs': dst_crs,
        'transform': dst_transform,
    }

    with rio.open(temp_path, 'w', **profile) as dst:
        rasterio.warp.reproject(
            source=da.values,
            destination=rasterio.band(dst, 1),
            src_transform=da.rio.transform(recalc=True),
            src_crs=src_crs,
            src_nodata=da.rio.nodata,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            dst_nodata=dst_nodata,
            resampling=resampling,
            **reprojection_kwargs,
        )

    shutil.move(temp_path, path)
