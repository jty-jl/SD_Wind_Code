#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate monthly and annual offshore wind resource and potential products from hourly gross CF.

Outputs:
- CF_mon_{region}.nc
- CF_year_{region}.nc
- CapacityDensity_{region}.nc
- Eden_mon_{scenario}_{region}.nc
- Eden_year_{scenario}_{region}.nc
- Tech_mon_{scenario}_{region}.nc
- Tech_year_{scenario}_{region}.nc
- Dev_mon_{scenario}_{dp_key}_{region}.nc
- Dev_year_{scenario}_{dp_key}_{region}.nc

Standard dimensions:
- Monthly products: Time, Lat, Lon
- Annual products: Time, Lat, Lon, where Time stores integer years
- Capacity density: scalar variables
"""

from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import xarray as xr
from dask.diagnostics import ProgressBar


SCENARIOS_CFG = {
    "Dense": {"kx": 7.0, "ky": 6.0, "eff_array": 0.83},
    "Moderate": {"kx": 9.0, "ky": 7.0, "eff_array": 0.88},
    "Sparse": {"kx": 11.0, "ky": 8.0, "eff_array": 0.93},
}

DP_FRACTIONS = {
    "p005": 0.005,
    "p01": 0.01,
    "p03": 0.03,
}

ENC_F32 = {
    "zlib": True,
    "complevel": 4,
    "dtype": "float32",
    "_FillValue": np.float32(np.nan),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate monthly and annual wind potential products from hourly gross CF."
    )
    parser.add_argument("--cf-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--region", default="offshore", choices=["offshore", "land", "onshore"])
    parser.add_argument("--cf-pattern", default="*.nc")
    parser.add_argument("--cf-var", default="CF")
    parser.add_argument("--rated-power-mw", default=11.525148634189092, type=float)
    parser.add_argument("--rotor-diameter-m", default=200.0, type=float)
    parser.add_argument("--availability-efficiency", default=0.95, type=float)
    parser.add_argument("--electrical-efficiency", default=0.98, type=float)
    return parser.parse_args()


def normalized_region_name(region):
    if region == "onshore":
        return "land"
    return region


def make_output_dirs(output_dir):
    dirs = {
        "CF_mon": output_dir / "CF_mon",
        "CF_year": output_dir / "CF_year",
        "CapDen": output_dir / "CapacityDensity",
        "Eden_mon": output_dir / "EnergyDensity_mon",
        "Eden_year": output_dir / "EnergyDensity_year",
        "Tech_mon": output_dir / "TechnicalPotential_mon",
        "Tech_year": output_dir / "TechnicalPotential_year",
        "Dev_mon": output_dir / "DevelopablePotential_mon",
        "Dev_year": output_dir / "DevelopablePotential_year",
    }

    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def standardize_dataset(ds):
    rename_dict = {}

    for name in list(ds.dims) + list(ds.coords):
        lower = name.lower()
        if lower in {"time", "valid_time"}:
            rename_dict[name] = "Time"
        elif lower in {"lat", "latitude"}:
            rename_dict[name] = "Lat"
        elif lower in {"lon", "longitude"}:
            rename_dict[name] = "Lon"

    if rename_dict:
        ds = ds.rename(rename_dict)

    return ds


def cell_area_km2(ds):
    lat = ds["Lat"].values
    lon = ds["Lon"].values

    dlat = abs(np.diff(lat)[0])
    dlon = abs(np.diff(lon)[0])

    radius_km = 6371.0
    lat_rad = np.deg2rad(lat)
    dlat_rad = np.deg2rad(dlat)
    dlon_rad = np.deg2rad(dlon)

    lat_north = lat_rad + dlat_rad / 2.0
    lat_south = lat_rad - dlat_rad / 2.0

    strip_area = (radius_km ** 2) * dlon_rad * (
        np.sin(lat_north) - np.sin(lat_south)
    )
    area = np.repeat(strip_area[:, np.newaxis], len(lon), axis=1)

    return xr.DataArray(
        area.astype("float32"),
        coords={"Lat": lat, "Lon": lon},
        dims=("Lat", "Lon"),
    )


def turbines_per_km2(rotor_diameter_m, kx, ky):
    turbine_area_km2 = (kx * rotor_diameter_m / 1000.0) * (
        ky * rotor_diameter_m / 1000.0
    )
    return 1.0 / turbine_area_km2


def set_time_for_monthly(da, year):
    expected_time = pd.date_range(f"{year}-01-01", f"{year}-12-01", freq="MS")
    da = da.assign_coords(Time=expected_time)
    return da.transpose("Time", "Lat", "Lon")


def set_time_for_annual(da, year):
    if "Time" not in da.dims:
        da = da.expand_dims(Time=[year])
    else:
        da = da.assign_coords(Time=[year])
    da["Time"].attrs["long_name"] = "Year"
    da["Time"].attrs["description"] = "Calendar year"
    return da.transpose("Time", "Lat", "Lon")


def save_dataarray(da, out_path, var_name, units, description, long_name):
    da = da.astype("float32")
    da.name = var_name
    da.attrs["units"] = units
    da.attrs["long_name"] = long_name
    da.attrs["description"] = description

    ds = da.to_dataset()
    with ProgressBar():
        ds.to_netcdf(out_path, encoding={var_name: ENC_F32})

    print(f"Saved: {out_path}")


def main():
    args = parse_args()

    region = normalized_region_name(args.region)
    dirs = make_output_dirs(args.output_dir)

    files = sorted(args.cf_dir.glob(args.cf_pattern))
    if not files:
        raise FileNotFoundError(f"No input NetCDF files found in {args.cf_dir}")

    with xr.open_dataset(files[0]) as ds0:
        ds0 = standardize_dataset(ds0)
        area_km2 = cell_area_km2(ds0)
        valid2d = np.isfinite(area_km2)

    ds_all = xr.open_mfdataset(
        files,
        preprocess=standardize_dataset,
        chunks={"Time": 720},
        parallel=True,
        combine="by_coords",
    )

    if args.cf_var not in ds_all.data_vars:
        raise KeyError(f"Variable '{args.cf_var}' not found in input files.")

    cf_hourly_gross = ds_all[args.cf_var].astype("float32").transpose("Time", "Lat", "Lon")

    cf_mon = cf_hourly_gross.resample(Time="1MS").mean(skipna=True).where(valid2d)
    cf_mon = set_time_for_monthly(cf_mon, args.year)

    save_dataarray(
        cf_mon,
        dirs["CF_mon"] / f"CF_mon_{region}.nc",
        "CF_mon",
        "dimensionless (0-1)",
        "Monthly mean wind capacity factor.",
        "Monthly mean wind capacity factor",
    )

    cf_year = cf_hourly_gross.mean(dim="Time", skipna=True).where(valid2d)
    cf_year = set_time_for_annual(cf_year, args.year)

    save_dataarray(
        cf_year,
        dirs["CF_year"] / f"CF_year_{region}.nc",
        "CF_year",
        "dimensionless (0-1)",
        "Annual mean wind capacity factor.",
        "Annual mean wind capacity factor",
    )

    turbine_gen_mon_gross = (
        cf_hourly_gross * args.rated_power_mw
    ).resample(Time="1MS").sum(skipna=True)

    turbine_gen_year_gross = (
        cf_hourly_gross * args.rated_power_mw
    ).sum(dim="Time", skipna=True)

    capden_vars = {}

    for scenario, cfg in SCENARIOS_CFG.items():
        kx = cfg["kx"]
        ky = cfg["ky"]
        eff_array = cfg["eff_array"]

        total_efficiency = (
            args.availability_efficiency
            * args.electrical_efficiency
            * eff_array
        )

        turbine_density = turbines_per_km2(args.rotor_diameter_m, kx, ky)

        cap_var = f"CapDen_{scenario}"
        capden_vars[cap_var] = xr.DataArray(
            np.float32(args.rated_power_mw * turbine_density),
            attrs={
                "units": "MW km-2",
                "long_name": f"Installed capacity density under the {scenario.lower()} layout scenario",
                "description": "Installed capacity density under the dense/moderate/sparse layout scenario.",
                "dimensions": "None (scalar)",
            },
        )

        eden_mon = (
            turbine_gen_mon_gross * total_efficiency * turbine_density
        ).where(valid2d)
        eden_mon = set_time_for_monthly(eden_mon, args.year)

        save_dataarray(
            eden_mon,
            dirs["Eden_mon"] / f"Eden_mon_{scenario}_{region}.nc",
            f"Eden_mon_{scenario}",
            "MWh/km2",
            "Monthly accumulated net energy generation per square kilometer.",
            "Monthly accumulated net energy generation per square kilometer",
        )

        eden_year = (
            turbine_gen_year_gross * total_efficiency * turbine_density
        ).where(valid2d)
        eden_year = set_time_for_annual(eden_year, args.year)

        save_dataarray(
            eden_year,
            dirs["Eden_year"] / f"Eden_year_{scenario}_{region}.nc",
            f"Eden_year_{scenario}",
            "MWh/km2",
            "Annual accumulated net energy generation per square kilometer.",
            "Annual accumulated net energy generation per square kilometer",
        )

        tech_mon = (eden_mon * area_km2).where(valid2d)

        save_dataarray(
            tech_mon,
            dirs["Tech_mon"] / f"Tech_mon_{scenario}_{region}.nc",
            f"Tech_mon_{scenario}",
            "MWh",
            "Monthly technical energy potential per grid cell.",
            "Monthly technical energy potential per grid cell",
        )

        tech_year = (eden_year * area_km2).where(valid2d)

        save_dataarray(
            tech_year,
            dirs["Tech_year"] / f"Tech_year_{scenario}_{region}.nc",
            f"Tech_year_{scenario}",
            "MWh",
            "Annual technical energy potential per grid cell.",
            "Annual technical energy potential per grid cell",
        )

        for dp_key, dp_fraction in DP_FRACTIONS.items():
            dev_mon = (tech_mon * dp_fraction).where(valid2d)

            save_dataarray(
                dev_mon,
                dirs["Dev_mon"] / f"Dev_mon_{scenario}_{dp_key}_{region}.nc",
                f"Dev_mon_{scenario}_{dp_key}",
                "MWh",
                "Monthly developable energy potential considering specific deployment potential ratios.",
                "Monthly developable energy potential considering specific deployment potential ratios",
            )

            dev_year = (tech_year * dp_fraction).where(valid2d)

            save_dataarray(
                dev_year,
                dirs["Dev_year"] / f"Dev_year_{scenario}_{dp_key}_{region}.nc",
                f"Dev_year_{scenario}_{dp_key}",
                "MWh",
                "Annual developable energy potential considering specific deployment potential ratios.",
                "Annual developable energy potential considering specific deployment potential ratios",
            )

    ds_cd = xr.Dataset(capden_vars)
    ds_cd.attrs["region"] = region
    ds_cd.attrs["frequency"] = "static"
    ds_cd.to_netcdf(dirs["CapDen"] / f"CapacityDensity_{region}.nc")

    ds_all.close()


if __name__ == "__main__":
    main()
