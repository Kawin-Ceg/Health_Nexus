"""Tamil Nadu health-centre registry used to seed valid_phc_facilities.

Every district in the state is covered, each with primary health centres named
after real towns and blocks in that district.

These rows are seeded with `is_placeholder = True`: the district and state are
correct, but the centre list is a stand-in for the official Tamil Nadu registry
(which has roughly 1,800 PHCs) and is not authoritative. Replace it by importing
the real registry and setting is_placeholder = False.

The first entries for Chennai, Chengalpattu, Tiruvallur and Kanchipuram keep the
order they were seeded with originally, so their facility codes do not move.
"""

STATE = "Tamil Nadu"

DISTRICTS: dict[str, tuple[str, ...]] = {
    "Ariyalur": ("Ariyalur", "Jayankondam", "Sendurai", "Andimadam"),
    "Chengalpattu": ("Tambaram", "Kattankulathur", "Chengalpattu", "Maraimalai Nagar", "Thiruporur", "Cheyyur"),
    "Chennai": ("Mylapore", "Adyar", "Ambattur", "Perambur", "Velachery", "Anna Nagar", "Thiruvottiyur", "Sholinganallur"),
    "Coimbatore": ("Coimbatore North", "Mettupalayam", "Pollachi", "Sulur", "Annur", "Kinathukadavu"),
    "Cuddalore": ("Cuddalore", "Chidambaram", "Panruti", "Virudhachalam", "Kurinjipadi"),
    "Dharmapuri": ("Dharmapuri", "Harur", "Palacode", "Pennagaram", "Karimangalam"),
    "Dindigul": ("Dindigul", "Palani", "Oddanchatram", "Natham", "Vedasandur"),
    "Erode": ("Erode", "Gobichettipalayam", "Bhavani", "Sathyamangalam", "Perundurai"),
    "Kallakurichi": ("Kallakurichi", "Chinnasalem", "Sankarapuram", "Ulundurpet"),
    "Kancheepuram": ("Sriperumbudur", "Kancheepuram", "Uthiramerur", "Walajabad"),
    "Kanyakumari": ("Nagercoil", "Kanyakumari", "Colachel", "Thuckalay", "Marthandam"),
    "Karur": ("Karur", "Kulithalai", "Krishnarayapuram", "Aravakurichi"),
    "Krishnagiri": ("Krishnagiri", "Hosur", "Denkanikottai", "Pochampalli", "Bargur"),
    "Madurai": ("Madurai South", "Melur", "Usilampatti", "Vadipatti", "Thirumangalam", "Peraiyur"),
    "Mayiladuthurai": ("Mayiladuthurai", "Sirkazhi", "Kuthalam", "Tharangambadi"),
    "Nagapattinam": ("Nagapattinam", "Vedaranyam", "Kilvelur", "Thirukkuvalai"),
    "Namakkal": ("Namakkal", "Rasipuram", "Tiruchengode", "Paramathi Velur", "Kolli Hills"),
    "Nilgiris": ("Udhagamandalam", "Coonoor", "Kotagiri", "Gudalur", "Pandalur"),
    "Perambalur": ("Perambalur", "Kunnam", "Veppanthattai", "Alathur"),
    "Pudukkottai": ("Pudukkottai", "Aranthangi", "Illuppur", "Karambakudi", "Gandarvakottai"),
    "Ramanathapuram": ("Ramanathapuram", "Paramakudi", "Rameswaram", "Kamuthi", "Mudukulathur"),
    "Ranipet": ("Ranipet", "Arakkonam", "Arcot", "Walajah", "Nemili"),
    "Salem": ("Salem South", "Attur", "Mettur", "Omalur", "Sankagiri", "Edappadi"),
    "Sivaganga": ("Sivaganga", "Karaikudi", "Devakottai", "Manamadurai", "Tirupathur"),
    "Tenkasi": ("Tenkasi", "Sankarankovil", "Shenkottai", "Alangulam", "Kadayanallur"),
    "Thanjavur": ("Thanjavur", "Kumbakonam", "Pattukkottai", "Papanasam", "Orathanadu"),
    "Theni": ("Theni", "Periyakulam", "Bodinayakanur", "Cumbum", "Andipatti"),
    "Thoothukudi": ("Thoothukudi", "Kovilpatti", "Tiruchendur", "Srivaikuntam", "Ettayapuram"),
    "Tiruchirappalli": ("Tiruchirappalli", "Srirangam", "Lalgudi", "Musiri", "Manapparai", "Thuraiyur"),
    "Tirunelveli": ("Palayamkottai", "Tirunelveli", "Ambasamudram", "Nanguneri", "Radhapuram"),
    "Tirupathur": ("Tirupathur", "Vaniyambadi", "Ambur", "Jolarpettai"),
    "Tiruppur": ("Tiruppur North", "Avinashi", "Udumalaipettai", "Dharapuram", "Palladam"),
    "Tiruvallur": ("Poonamallee", "Villivakkam", "Tiruvallur", "Gummidipoondi", "Ponneri", "Pallipattu"),
    "Tiruvannamalai": ("Tiruvannamalai", "Arani", "Cheyyar", "Polur", "Chengam"),
    "Tiruvarur": ("Tiruvarur", "Mannargudi", "Needamangalam", "Thiruthuraipoondi"),
    "Vellore": ("Vellore", "Katpadi", "Gudiyatham", "Anaicut", "K V Kuppam"),
    "Viluppuram": ("Viluppuram", "Tindivanam", "Gingee", "Vanur", "Marakkanam"),
    "Virudhunagar": ("Virudhunagar", "Sivakasi", "Rajapalayam", "Srivilliputhur", "Aruppukottai"),
}

CODES: dict[str, str] = {
    "Ariyalur": "ARY",
    "Chengalpattu": "CGL",
    "Chennai": "CHN",
    "Coimbatore": "CBE",
    "Cuddalore": "CUD",
    "Dharmapuri": "DPI",
    "Dindigul": "DGL",
    "Erode": "ERD",
    "Kallakurichi": "KLK",
    "Kancheepuram": "KPM",
    "Kanyakumari": "KNY",
    "Karur": "KRR",
    "Krishnagiri": "KGI",
    "Madurai": "MDU",
    "Mayiladuthurai": "MYL",
    "Nagapattinam": "NGP",
    "Namakkal": "NMK",
    "Nilgiris": "NLG",
    "Perambalur": "PBR",
    "Pudukkottai": "PDK",
    "Ramanathapuram": "RMD",
    "Ranipet": "RPT",
    "Salem": "SLM",
    "Sivaganga": "SVG",
    "Tenkasi": "TKS",
    "Thanjavur": "TNJ",
    "Theni": "TEN",
    "Thoothukudi": "TUT",
    "Tiruchirappalli": "TRY",
    "Tirunelveli": "TNL",
    "Tirupathur": "TPT",
    "Tiruppur": "TUP",
    "Tiruvallur": "TVL",
    "Tiruvannamalai": "TVM",
    "Tiruvarur": "TVR",
    "Vellore": "VLR",
    "Viluppuram": "VLP",
    "Virudhunagar": "VNR",
}

COORDS: dict[str, tuple[float, float]] = {
    "Mylapore": (13.0339, 80.2619),
    "Adyar": (13.0012, 80.2565),
    "Ambattur": (13.1143, 80.1548),
    "Perambur": (13.1187, 80.2332),
    "Velachery": (12.9791, 80.2181),
    "Anna Nagar": (13.0850, 80.2101),
    "Thiruvottiyur": (13.1580, 80.3009),
    "Sholinganallur": (12.9010, 80.2279),
    "Tambaram": (12.9249, 80.1000),
    "Kattankulathur": (12.8456, 80.0598),
    "Chengalpattu": (12.6819, 79.9888),
    "Poonamallee": (13.0473, 80.0945),
    "Villivakkam": (13.1067, 80.1010),
    "Tiruvallur": (13.1439, 79.9094),
    "Sriperumbudur": (12.9675, 79.9419),
    "Kancheepuram": (12.8342, 79.7036),
    "Coimbatore North": (11.0168, 76.9558),
    "Madurai South": (9.9252, 78.1198),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Salem South": (11.6643, 78.1460),
    "Thanjavur": (10.7870, 79.1378),
    "Vellore": (12.9165, 79.1325),
    "Nagercoil": (8.1833, 77.4119),
    "Erode": (11.3410, 77.7172),
    "Tiruppur North": (11.1085, 77.3411),
    "Thoothukudi": (8.7642, 78.1348),
    "Palayamkottai": (8.7139, 77.7567),
    "Udhagamandalam": (11.4102, 76.6950),
}


def facilities() -> list[dict]:
    """Every facility row to seed, in a stable order."""
    rows: list[dict] = []
    for district, towns in DISTRICTS.items():
        prefix = CODES[district]
        for i, town in enumerate(towns, start=1):
            lat, lng = COORDS.get(town, (None, None))
            rows.append(
                {
                    "facility_code": f"TN-{prefix}-PHC-{i:03d}",
                    "name": f"{town} PHC",
                    "district": district,
                    "state": STATE,
                    "block": town,
                    "latitude": lat,
                    "longitude": lng,
                }
            )
    return rows
