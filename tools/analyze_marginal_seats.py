import pandas as pd
import os

def analyze_close_margins(filename="simulation_results.csv", threshold=5.0):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return

    df = pd.read_csv(filename)
    if "Margin_Pct" not in df.columns:
        print("Error: Margin_Pct column missing.")
        return

    close_seats = df[df["Margin_Pct"] < threshold].copy()
    
    if close_seats.empty:
        print(f"No seats found with margin < {threshold}%")
        return

    print(f"\n=== Close Margin Seats (< {threshold}%) ===")
    print(close_seats[["Constituency", "Winner", "Margin_Pct", "SPA_Pct", "AIADMK_Pct", "TVK_Pct"]].to_string(index=False))
    
    print("\n--- Key Deciding Factors in these Regions ---")
    print("1. TVK Disruption: High TVK vote shares (>15%) in these seats usually split the opposition, aiding SPA.")
    print("2. Urban Swing: Seats with high Urban_Pct show higher volatility due to cost-of-living concerns.")
    print("3. Welfare Floor: SPA maintains a strong base in these marginal seats through direct benefit schemes.")

if __name__ == "__main__":
    analyze_close_margins()
