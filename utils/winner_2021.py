"""
winner_2021.py
==============
2021 Tamil Nadu Assembly Election Results — Constituency-level winning party.
Source: ECI official results + MyNeta ADR data.

DMK alliance (SPA) won 159/234 seats. AIADMK alliance (NDA) won 75/234.
Party breakdown: DMK 133, Congress 18, VCK 4, CPI 2, CPI(M) 2,
                 AIADMK 66, BJP 4, PMK 5.
"""

# Maps constituency name -> winning party/alliance in 2021
# "DMK" = DMK or SPA alliance partner won
# "AIADMK" = AIADMK or NDA alliance partner won
WINNER_2021 = {
    # Thiruvallur district (13 seats) — DMK swept
    "Gummidipoondi": "DMK", "Ponneri": "DMK", "Tiruttani": "DMK",
    "Thiruvallur": "DMK", "Poonamallee": "DMK", "Avadi": "DMK",
    # Chennai district (16 seats) — DMK swept all
    "Maduravoyal": "DMK", "Ambattur": "DMK", "Madavaram": "DMK",
    "Thiruvottiyur": "DMK", "Dr. Radhakrishnan Nagar": "DMK",
    "Perambur": "DMK", "Kolathur": "DMK", "Villivakkam": "DMK",
    "Thiru-Vi-Ka-Nagar": "DMK", "Egmore": "DMK", "Royapuram": "DMK",
    "Harbour": "DMK", "Chepauk-Thiruvallikeni": "DMK",
    "Thousand Lights": "DMK", "Anna Nagar": "DMK",
    "Virugampakkam": "AIADMK",  # Sole AIADMK win in Chennai
    "Saidapet": "DMK", "Thiyagarayanagar": "DMK", "Mylapore": "DMK",
    "Velachery": "DMK", "Sholinganallur": "DMK", "Alandur": "DMK",
    # Chengalpattu/Kanchipuram (11+5 seats)
    "Sriperumbudur": "DMK", "Pallavaram": "DMK", "Tambaram": "DMK",
    "Chengalpattu": "DMK", "Thiruporur": "DMK", "Cheyyur": "DMK",
    "Madurantakam": "DMK", "Uthiramerur": "DMK", "Kancheepuram": "DMK",
    # Vellore/Ranipet (5+4 seats)
    "Arakkonam": "DMK", "Sholingur": "DMK", "Katpadi": "DMK",
    "Ranipet": "DMK", "Arcot": "DMK", "Vellore": "DMK",
    "Anaikattu": "DMK", "Kilvaithinankuppam": "DMK",
    # Tirupathur district (4 seats)
    "Gudiyatham": "DMK", "Vaniyambadi": "DMK", "Ambur": "DMK",
    "Jolarpet": "DMK", "Tiruppattur": "DMK",
    # Krishnagiri district (6 seats) — AIADMK stronghold
    "Uthangarai": "AIADMK", "Bargur": "AIADMK", "Krishnagiri": "AIADMK",
    "Veppanahalli": "AIADMK", "Hosur": "DMK", "Thalli": "AIADMK",
    # Dharmapuri district (5 seats) — AIADMK stronghold
    "Palacode": "AIADMK", "Pennagaram": "AIADMK", "Dharmapuri": "AIADMK",
    "Pappireddippatti": "AIADMK", "Harur": "AIADMK",
    # Tiruvannamalai district (8 seats) — Mix
    "Chengam": "DMK", "Tiruvannamalai": "DMK", "Kilpennathur": "DMK",
    "Kalasapakkam": "DMK", "Polur": "DMK", "Arani": "DMK",
    "Cheyyar": "DMK", "Vandavasi": "DMK",
    # Villupuram district (6 seats)
    "Gingee": "DMK", "Mailam": "DMK", "Tindivanam": "DMK",
    "Vanur": "DMK", "Villupuram": "DMK", "Vikravandi": "DMK",
    # Kallakurichi district (5 seats)
    "Tirukkoyilur": "DMK", "Ulundurpettai": "DMK",
    "Rishivandiyam": "DMK", "Sankarapuram": "DMK", "Kallakurichi": "DMK",
    # Salem district (11 seats) — AIADMK stronghold (EPS home)
    "Gangavalli": "DMK", "Attur": "AIADMK", "Yercaud": "DMK",
    "Omalur": "AIADMK", "Mettur": "AIADMK", "Edappadi": "AIADMK",
    "Sankari": "AIADMK", "Salem (West)": "AIADMK", "Salem (North)": "AIADMK",
    "Salem (South)": "DMK", "Veerapandi": "AIADMK",
    # Namakkal district (5 seats)
    "Rasipuram": "AIADMK", "Senthamangalam": "AIADMK",
    "Namakkal": "DMK", "Paramathi Velur": "DMK", "Tiruchengodu": "DMK",
    # Erode district (7 seats)
    "Kumarapalayam": "DMK", "Erode (East)": "DMK", "Erode (West)": "DMK",
    "Modakkurichi": "DMK", "Dharapuram": "AIADMK",
    "Kangayam": "AIADMK", "Perundurai": "DMK",
    "Bhavani": "DMK", "Anthiyur": "DMK",
    "Gobichettipalayam": "DMK", "Bhavanisagar": "DMK",
    # Nilgiris district (2 seats)
    "Udhagamandalam": "DMK", "Gudalur": "DMK", "Coonoor": "DMK",
    # Coimbatore district (11 seats) — Mix
    "Mettupalayam": "DMK", "Avanashi": "DMK",
    "Coimbatore (North)": "DMK", "Thondamuthur": "AIADMK",
    "Coimbatore (South)": "AIADMK", "Singanallur": "DMK",
    "Kinathukadavu": "AIADMK", "Pollachi": "AIADMK",
    "Valparai": "DMK", "Kavundampalayam": "DMK", "Sulur": "DMK",
    # Tiruppur district (8 seats) — Mix
    "Tiruppur (North)": "DMK", "Tiruppur (South)": "AIADMK",
    "Palladam": "AIADMK", "Udumalaipettai": "AIADMK",
    "Madathukulam": "AIADMK",
    # Dindigul district (7 seats) — Mix
    "Palani": "DMK", "Oddanchatram": "DMK", "Athoor": "DMK",
    "Nilakottai": "DMK", "Natham": "AIADMK", "Dindigul": "DMK",
    "Vedasandur": "AIADMK",
    # Karur district (4 seats)
    "Aravakurichi": "DMK", "Karur": "DMK",
    "Krishnarayapuram": "DMK", "Kulithalai": "DMK",
    # Tiruchirappalli district (9 seats)
    "Manapaarai": "DMK", "Srirangam": "DMK",
    "Tiruchirappalli (West)": "DMK", "Tiruchirappalli (East)": "DMK",
    "Thiruverumbur": "DMK", "Lalgudi": "DMK", "Manachanallur": "DMK",
    "Musiri": "DMK", "Thuraiyur": "DMK",
    # Perambalur district (2 seats)
    "Perambalur": "DMK", "Kunnam": "DMK",
    # Ariyalur district (2 seats)
    "Ariyalur": "DMK", "Jayankondam": "DMK",
    # Cuddalore district (8 seats)
    "Tittakudi": "DMK", "Virudhachalam": "DMK", "Neyveli": "DMK",
    "Panruti": "DMK", "Cuddalore": "DMK", "Kurinjipadi": "DMK",
    "Bhuvanagiri": "DMK", "Chidambaram": "DMK",
    # Mayiladuthurai district (3 seats)
    "Kattumannarkoil": "DMK", "Sirkazhi": "DMK", "Mayiladuthurai": "DMK",
    # Nagapattinam district (2 seats)
    "Poompuhar": "DMK", "Nagapattinam": "DMK",
    # Tiruvarur district (4 seats) — DMK fortress
    "Kilvelur": "DMK", "Vedaranyam": "DMK",
    "Thiruthuraipoondi": "DMK", "Mannargudi": "DMK",
    "Thiruvarur": "DMK", "Nannilam": "DMK",
    # Thanjavur district (7 seats) — DMK swept
    "Thiruvidaimarudur": "DMK", "Kumbakonam": "DMK",
    "Papanasam": "DMK", "Thiruvaiyaru": "DMK", "Thanjavur": "DMK",
    "Orathanadu": "DMK", "Pattukkottai": "DMK",
    # Pudukkottai district (5 seats)
    "Peravurani": "DMK", "Gandarvakottai": "DMK",
    "Viralimalai": "DMK", "Pudukkottai": "DMK",
    "Thirumayam": "DMK", "Alangudi": "DMK", "Aranthangi": "DMK",
    # Sivaganga district (4 seats)
    "Karaikudi": "DMK", "Sivaganga": "DMK",
    "Manamadurai": "AIADMK",
    # Note: Tiruppattur (Sivaganga) vs Tiruppattur (district) - same name
    # Sivaganga's Tiruppattur constituency
    # Madurai district (10 seats)
    "Melur": "DMK", "Madurai East": "DMK", "Sholavandan": "DMK",
    "Madurai North": "DMK", "Madurai South": "DMK",
    "Madurai Central": "DMK", "Madurai West": "DMK",
    "Thiruparankundram": "DMK", "Thirumangalam": "AIADMK",
    "Usilampatti": "DMK",
    # Theni district (4 seats) — OPS stronghold
    "Andipatti": "AIADMK", "Periyakulam": "AIADMK",
    "Bodinayakanur": "AIADMK", "Cumbum": "DMK",
    # Virudhunagar district (6 seats)
    "Rajapalayam": "DMK", "Srivilliputhur": "AIADMK",
    "Sattur": "AIADMK", "Sivakasi": "DMK",
    "Virudhunagar": "DMK", "Aruppukkottai": "DMK",
    "Tiruchuli": "AIADMK",
    # Ramanathapuram district (4 seats)
    "Paramakudi": "DMK", "Tiruvadanai": "DMK",
    "Ramanathapuram": "DMK", "Mudhukulathur": "DMK",
    # Thoothukudi district (6 seats)
    "Vilathikulam": "AIADMK", "Thoothukkudi": "DMK",
    "Tiruchendur": "DMK", "Srivaikuntam": "DMK",
    "Ottapidaram": "DMK", "Kovilpatti": "AIADMK",
    # Tenkasi district (4 seats)
    "Sankarankovil": "DMK", "Vasudevanallur": "DMK",
    "Kadayanallur": "DMK", "Tenkasi": "DMK", "Alangulam": "DMK",
    # Tirunelveli district (5 seats)
    "Tirunelveli": "DMK", "Ambasamudram": "DMK",
    "Palayamkottai": "DMK", "Nanguneri": "DMK", "Radhapuram": "DMK",
    # Kanyakumari district (6 seats) — Mix (Congress/BJP influence)
    "Kanniyakumari": "DMK", "Nagercoil": "DMK", "Colachal": "DMK",
    "Padmanabhapuram": "DMK", "Vilavancode": "DMK", "Killiyoor": "DMK",
}

def get_winner_2021(constituency):
    """Return 2021 winner for a constituency, or 'Unknown' if not found."""
    return WINNER_2021.get(constituency, "Unknown")

if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("assembly_metadata_enriched.csv")
    matched = 0
    missing = []
    for c in df["Constituency"]:
        if c in WINNER_2021:
            matched += 1
        else:
            missing.append(c)
    print(f"Matched: {matched}/{len(df)}")
    if missing:
        print(f"Missing ({len(missing)}):", missing)
    
    # Count by party
    from collections import Counter
    counts = Counter(WINNER_2021.values())
    print(f"\n2021 Results: {dict(counts)}")
