"""
smoke_test.py — Run 1 constituency simulation
"""
import os, sys
sys.path.append(os.getcwd())
from core.voter_agent_engine import run_simulation

def main():
    print("Starting 1-constituency smoke test...")
    run_simulation(limit=1)
    print("Smoke test complete.")

if __name__ == "__main__":
    main()
