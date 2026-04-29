import pandas as pd

df = pd.read_csv('assembly_metadata_enriched.csv')

print("=== WHAT WE HAVE ===")
print(f"Total columns: {len(df.columns)}")
print(f"Reserved seats: {df['Reserved'].value_counts().to_dict()}")
print(f"\nTurnout stats (2021 vs 2026):")
print(df[['Turnout_2021','Turnout_2026','Turnout_Delta']].describe().round(2))

print("\n=== MISSING PREDICTION FACTORS ===")
missing = [
    ('Margin_2021',      'HIGH',   '2021 victory margin - tells if seat is safe vs marginal'),
    ('Win_Pct_2021',     'HIGH',   '2021 winner vote share % - measures stronghold strength'),
    ('Incumbent_Running','HIGH',   'Is 2021 winner standing again? Incumbency boost/anti factor'),
    ('Defeat_Margin_2021','HIGH',  'Losing margin for runner-up - gauges swing needed'),
    ('SC_ST_Pct',        'HIGH',   'Dalit/Tribal voter % - VCK/BSP/Left alignment factor'),
    ('Muslim_Pct',       'HIGH',   'Muslim voter % - SPA loyalty factor (IUML, DMK base)'),
    ('OBC_Pct',          'MEDIUM', 'OBC/MBC % - PMK, TVK, AIADMK competition zone'),
    ('TVK_Candidate_Strength','HIGH','TVK has strong candidate here? Critical for 3-way split'),
    ('Anti_Incumbency_Score','HIGH','Calculated 5-yr local governance score'),
    ('Welfare_Penetration','MEDIUM','% households receiving Magalir/Kalaignar welfare'),
    ('Unemployment_Index','MEDIUM','Local youth unemployment indicator'),
    ('Turnout_Delta_Direction','HIGH','High turnout surge = challenger benefit or base consolidation?'),
    ('Swing_2021_to_2026','HIGH',  'Predicted % swing from 2021 result'),
    ('Alliance_Seat_Share','HIGH', 'AIADMK vs BJP split - NDA field own or combined candidate?'),
    ('Border_Dispute_Factor','LOW','Cauvery/inter-state factor for specific constituencies'),
]

for col, impact, desc in missing:
    in_df = col in df.columns
    status = "EXISTS" if in_df else "MISSING"
    print(f"  [{impact}] {col}: {status} -- {desc}")

print("\n=== FACTORS PARTIALLY AVAILABLE ===")
partial = [
    ('Reserved',        'SC/ST reservation flag exists but no SC% population data'),
    ('Turnout_Delta',   'Delta exists but direction (anti-incumbency vs base mobilization) not modeled'),
    ('Voter_Profile',   'Exists but not fed into LLM prompt'),
    ('Female_Voters',   'Count exists, but Magalir scheme penetration not factored'),
    ('Youth_Voters',    'Count exists, but TVK youth mobilization index missing'),
    ('Winner_2021',     'Party known, but margin/vote-share unknown'),
]
for col, note in partial:
    print(f"  {col}: {note}")

print("\n=== HIGHEST IMPACT MISSING FACTORS ===")
print("""
1. SEAT MARGINALITY (2021 victory margin):
   - Seats won by <5k votes in 2021 are SWING seats
   - Seats won by >25k are SAFE seats (near-certain outcome)
   - This single factor would dramatically improve seat-level accuracy

2. INCUMBENT MLA RE-CONTESTING:
   - Incumbent re-contesting = anti-incumbency vote mobilizes
   - Fresh candidate = party-wave vote dominates
   - TVK factor strongest in seats where incumbent is unpopular

3. TVK CANDIDATE QUALITY:
   - In seats with a high-profile TVK candidate, vote share can be 15-25%
   - In seats without, TVK is a spoiler at 5-8%
   - Currently all seats get same TVK sentiment baseline

4. SC/ST POPULATION % (Reserved + General):
   - SC seats = VCK/Left bloc guaranteed base for SPA
   - High SC % in general seats also boosts SPA
   - AIADMK has poor SC connect since 2021

5. TURNOUT DELTA DIRECTION:
   - Your data shows +10.5% average surge in 2026
   - This typically benefits challenger (anti-incumbency)
   - But in SPA welfare strongholds, it means base consolidation
   - Not currently modeled in fallback or prompt
""")
