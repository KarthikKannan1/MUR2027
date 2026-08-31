from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Tunable model constants
FUEL_EFFECT_S_PER_KG = 0.030   
START_FUEL_KG = 110.0          
CACHE_DIR = "./ff1_cache"


def setup(cache_dir: str = CACHE_DIR) -> None:
    import os
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)
    fastf1.plotting.setup_mpl(mpl_timedelta_support=True, color_scheme="fastf1")


def clean_laps(laps: "fastf1.core.Laps") -> pd.DataFrame:
    df = laps.copy()
    df = df[df["PitInTime"].isna() & df["PitOutTime"].isna()]
    if "TrackStatus" in df.columns:
        df = df[df["TrackStatus"] == "1"]
    df = df.dropna(subset=["LapTime", "TyreLife", "Compound", "Stint"])
    return df


def fuel_corrected_seconds(lap_number: pd.Series, total_laps: int) -> pd.Series:
    frac_remaining = np.clip(1 - (lap_number - 1) / max(total_laps - 1, 1), 0, 1)
    fuel_kg_remaining = frac_remaining * START_FUEL_KG
    return fuel_kg_remaining * FUEL_EFFECT_S_PER_KG


def prep_driver_laps(session: "fastf1.core.Session", driver: str) -> pd.DataFrame:
    laps = session.laps.pick_drivers(driver)
    df = clean_laps(laps)
    if df.empty:
        return df
    total_laps = session.total_laps or int(df["LapNumber"].max())
    df = df.copy()
    df["LapTimeSeconds"] = df["LapTime"].dt.total_seconds()
    df["FuelPenalty"] = fuel_corrected_seconds(df["LapNumber"], total_laps)
    df["FuelCorrectedSeconds"] = df["LapTimeSeconds"] - df["FuelPenalty"]
    return df


@dataclass
class StintFit:
    stint: int
    compound: str
    n_laps: int
    intercept_s: float  
    slope_s_per_lap: float 
    r2: float


def fit_stint_degradation(df: pd.DataFrame) -> list[StintFit]:
    fits = []
    for (stint, compound), g in df.groupby(["Stint", "Compound"]):
        g = g.sort_values("TyreLife")
        if len(g) < 3:
            continue  # not enough points for a meaningful fit
        x = g["TyreLife"].to_numpy(dtype=float)
        y = g["FuelCorrectedSeconds"].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        fits.append(StintFit(int(stint), str(compound), len(g), intercept, slope, r2))
    return sorted(fits, key=lambda f: f.stint)


# 1. Single-race stint / degradation plot
def plot_stint_degradation(year: int, event: str, session_type: str, driver: str,
                            save_path: str | None = None):
    session = fastf1.get_session(year, event, session_type)
    session.load()

    df = prep_driver_laps(session, driver)
    if df.empty:
        raise ValueError(f"No usable laps found for {driver} in {year} {event} {session_type}")

    fits = fit_stint_degradation(df)

    fig, ax = plt.subplots(figsize=(10, 6))
    compound_colors = {}  
    for fit in fits:
        stint_df = df[(df["Stint"] == fit.stint) & (df["Compound"] == fit.compound)].sort_values("TyreLife")
        color = compound_colors.setdefault(
            fit.compound, fastf1.plotting.get_compound_color(fit.compound, session=session)
        )
        ax.scatter(stint_df["TyreLife"], stint_df["FuelCorrectedSeconds"],
                   color=color, s=28, alpha=0.85,
                   label=f"Stint {fit.stint} ({fit.compound}, {fit.slope_s_per_lap:+.3f} s/lap)")
        x_line = np.array([stint_df["TyreLife"].min(), stint_df["TyreLife"].max()])
        y_line = fit.slope_s_per_lap * x_line + fit.intercept_s
        ax.plot(x_line, y_line, color=color, lw=2, alpha=0.6)

    ax.set_xlabel("Tyre life (laps on this set)")
    ax.set_ylabel("Fuel-corrected lap time (s)")
    ax.set_title(f"{driver} -- {year} {event} ({session_type}) -- Fuel-corrected tyre degradation")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=140)
    return fig, fits


# 2. Season drop-off trend
def season_dropoff(year: int, driver: str, verbose: bool = True) -> pd.DataFrame:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    rows = []
    for _, event_row in schedule.iterrows():
        event_name = event_row["EventName"]
        try:
            session = fastf1.get_session(year, event_name, "R")
            session.load()
        except Exception as e:  # missing session, cancelled event, etc.
            if verbose:
                print(f"  [skip] {event_name}: {e}")
            continue

        df = prep_driver_laps(session, driver)
        if df.empty:
            continue

        fits = fit_stint_degradation(df)
        avg_slope = np.mean([f.slope_s_per_lap for f in fits]) if fits else np.nan

        field_clean = clean_laps(session.laps)
        if field_clean.empty:
            continue
        field_clean = field_clean.copy()
        total_laps = session.total_laps or int(field_clean["LapNumber"].max())
        field_clean["FuelCorrectedSeconds"] = (
            field_clean["LapTime"].dt.total_seconds()
            - fuel_corrected_seconds(field_clean["LapNumber"], total_laps)
        )
        field_best = field_clean["FuelCorrectedSeconds"].min()
        driver_median = df["FuelCorrectedSeconds"].median()
        gap = driver_median - field_best

        rows.append({
            "Round": event_row["RoundNumber"],
            "Event": event_name,
            "AvgDegradation_s_per_lap": avg_slope,
            "CompetitiveGap_s": gap,
        })
        if verbose:
            print(f"  [ok]   {event_name}: deg={avg_slope:.3f} s/lap, gap={gap:.3f} s")

    return pd.DataFrame(rows).sort_values("Round").reset_index(drop=True)

def plot_season_dropoff(year: int, driver: str, save_path: str | None = None):
    print(f"Fetching {year} season data for {driver} -- this loads every race "
          f"weekend and can take a few minutes the first time (cached after that).")
    data = season_dropoff(year, driver)
    if data.empty:
        raise ValueError(f"No race data found for {driver} in {year}")

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)

    axes[0].plot(data["Round"], data["AvgDegradation_s_per_lap"], "o-", color="#d1242f")
    axes[0].axhline(0, color="grey", lw=0.6)
    axes[0].set_ylabel("Avg degradation\n(s/lap)")
    axes[0].set_title(f"{driver} -- {year} Season: Tyre Degradation & Competitive Gap Trend")
    axes[0].grid(alpha=0.25)

    axes[1].plot(data["Round"], data["CompetitiveGap_s"], "o-", color="#1f6feb")
    axes[1].set_ylabel("Gap to fastest\nfuel-corrected lap (s)")
    axes[1].set_xlabel("Round")
    axes[1].grid(alpha=0.25)

    axes[1].set_xticks(data["Round"])
    axes[1].set_xticklabels(data["Event"], rotation=60, ha="right", fontsize=7)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=140)
    return fig, data


# 3. Telemetry comparison
def plot_telemetry_comparison(year: int, event: str, session_type: str,
                               drivers: list[str], save_path: str | None = None):
    session = fastf1.get_session(year, event, session_type)
    session.load()

    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for drv in drivers:
        lap = session.laps.pick_drivers(drv).pick_fastest()
        tel = lap.get_car_data().add_distance()
        color = fastf1.plotting.get_driver_color(drv, session=session)
        axes[0].plot(tel["Distance"], tel["Speed"], label=drv, color=color)
        axes[1].plot(tel["Distance"], tel["Throttle"], label=drv, color=color)
        axes[2].plot(tel["Distance"], tel["Brake"].astype(int), label=drv, color=color)

    axes[0].set_ylabel("Speed (km/h)")
    axes[1].set_ylabel("Throttle (%)")
    axes[2].set_ylabel("Brake")
    axes[2].set_xlabel("Distance (m)")
    axes[0].set_title(f"{year} {event} ({session_type}) -- Fastest lap telemetry")
    axes[0].legend()
    for ax in axes:
        ax.grid(alpha=0.25)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=140)
    return fig


# CLI
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_stint = sub.add_parser("stint", help="Fuel-corrected degradation plot for one driver/race")
    p_stint.add_argument("--year", type=int, required=True)
    p_stint.add_argument("--event", type=str, required=True, help='e.g. "Silverstone", "Monaco"')
    p_stint.add_argument("--session", type=str, default="R", help="FP1/FP2/FP3/Q/S/R (default R)")
    p_stint.add_argument("--driver", type=str, required=True, help="3-letter code, e.g. VER")
    p_stint.add_argument("--save", type=str, default=None, help="Path to save PNG")

    p_season = sub.add_parser("season", help="Season-long degradation & competitive-gap trend")
    p_season.add_argument("--year", type=int, required=True)
    p_season.add_argument("--driver", type=str, required=True)
    p_season.add_argument("--save", type=str, default=None)
    p_season.add_argument("--csv", type=str, default=None, help="Also dump the raw season table to CSV")

    p_cmp = sub.add_parser("compare", help="Overlay fastest-lap telemetry for 2+ drivers")
    p_cmp.add_argument("--year", type=int, required=True)
    p_cmp.add_argument("--event", type=str, required=True)
    p_cmp.add_argument("--session", type=str, default="Q")
    p_cmp.add_argument("--drivers", type=str, nargs="+", required=True)
    p_cmp.add_argument("--save", type=str, default=None)

    args = parser.parse_args()
    setup()

    if args.command == "stint":
        fig, fits = plot_stint_degradation(args.year, args.event, args.session, args.driver, args.save)
        for f in fits:
            print(f"Stint {f.stint} ({f.compound}, {f.n_laps} laps): "
                  f"{f.slope_s_per_lap:+.3f} s/lap degradation, "
                  f"fresh-tyre pace {f.intercept_s:.3f}s, R^2={f.r2:.2f}")
        plt.show()

    elif args.command == "season":
        fig, data = plot_season_dropoff(args.year, args.driver, args.save)
        if args.csv:
            data.to_csv(args.csv, index=False)
            print(f"Season table written to {args.csv}")
        plt.show()

    elif args.command == "compare":
        plot_telemetry_comparison(args.year, args.event, args.session, args.drivers, args.save)
        plt.show()


if __name__ == "__main__":
    sys.exit(main())