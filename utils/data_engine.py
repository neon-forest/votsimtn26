"""
data_engine.py
==============
Now a thin loader/reporter only.
All vote calculation is done in voter_agent_engine.py which writes simulation_results.csv.
This module just validates the results and exposes run_simulation() for app.py compatibility.
"""

import pandas as pd
import numpy as np
import os

from utils.paths import get_data_path

def load_simulation_results():
    """
    Load the simulation_results.csv produced by the simulation engine.
    Returns a DataFrame ready for the dashboard.
    """
    path = get_data_path("simulation_results.csv")
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)

    # Compute derived columns for dashboard compatibility
    if "Turnout_2026" not in df.columns:
        # Merge turnout from assembly metadata if missing
        meta_path = get_data_path("assembly_metadata.csv")
        if os.path.exists(meta_path):
            meta = pd.read_csv(meta_path)
            meta["Seat_Registered"] = (meta["Registered_Voters"] / meta["Assembly_Seats"]).astype(int)
            df = pd.merge(df, meta[["Constituency", "Turnout_2026", "Turnout_Delta",
                                     "GDP_Lakhs", "Seat_Registered"]], on="Constituency", how="left")
            df.rename(columns={"Seat_Registered": "Registered_Voters"}, inplace=True)

    # Flip probability: high turnout delta + narrow margin = high risk
    if "Flip_Probability" not in df.columns and "Turnout_Delta" in df.columns:
        df["Flip_Probability"] = (
            df["Turnout_Delta"] * 5 +
            df["Margin_Pct"].apply(lambda m: 3 if m < 5 else 0)
        ).clip(5, 99).round(2)

    return df


def run_simulation():
    """
    Entry point for app.py. Runs core engine if results are missing,
    otherwise just loads existing results.
    """
    results_path = get_data_path("simulation_results.csv")

    if not os.path.exists(results_path):
        print("No simulation_results.csv found. Running simulation engine...")
        from core.voter_agent_engine import run_simulation as start_sim
        start_sim()

    return load_simulation_results()


if __name__ == "__main__":
    df = run_simulation()
    if df.empty:
        print("No results — run voter_agent_engine.py first.")
    else:
        print(f"Loaded {len(df)} constituency results.")
        print(df[["Constituency", "Winner", "Winning_Votes", "Margin_Votes", "Margin_Pct"]].head(10).to_string())
        print("\nSeat Tally:")
        print(df["Winner"].value_counts().to_string())
