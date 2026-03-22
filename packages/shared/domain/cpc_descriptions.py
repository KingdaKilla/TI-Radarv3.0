"""CPC-Klassifikationsbeschreibungen (WIPO/EPO Cooperative Patent Classification).

Stellt Beschreibungen fuer CPC-Sektionen, -Klassen und -Subklassen bereit.
Datenquelle: WIPO CPC Scheme (oeffentlich), reduziert auf die ~200 haeufigsten Codes.
"""

from __future__ import annotations

# --- CPC Sektionen (Level 1) ---

CPC_SECTION_DESCRIPTIONS: dict[str, str] = {
    "A": "Human Necessities",
    "B": "Performing Operations; Transporting",
    "C": "Chemistry; Metallurgy",
    "D": "Textiles; Paper",
    "E": "Fixed Constructions",
    "F": "Mechanical Engineering; Lighting; Heating; Weapons; Blasting",
    "G": "Physics",
    "H": "Electricity",
    "Y": "General Tagging of New Technological Developments",
}


# --- CPC Klassen (Level 3, z.B. "A01", "G06") ---

CPC_CLASS_DESCRIPTIONS: dict[str, str] = {
    # A — Human Necessities
    "A01": "Agriculture; Forestry; Animal Husbandry",
    "A21": "Baking; Edible Doughs",
    "A22": "Butchering; Meat Treatment",
    "A23": "Foods or Foodstuffs; Treatment Thereof",
    "A24": "Tobacco; Cigars; Cigarettes",
    "A41": "Wearing Apparel",
    "A42": "Headwear",
    "A43": "Footwear",
    "A44": "Haberdashery; Jewellery",
    "A45": "Hand or Travelling Articles",
    "A46": "Brushware",
    "A47": "Furniture; Domestic Articles; Coffee/Tea Mills",
    "A61": "Medical or Veterinary Science; Hygiene",
    "A62": "Life-Saving; Fire-Fighting",
    "A63": "Sports; Games; Amusements",
    # B — Operations; Transport
    "B01": "Physical or Chemical Processes or Apparatus",
    "B02": "Crushing, Pulverising, Disintegrating",
    "B03": "Separation of Solid Materials",
    "B04": "Centrifugal Apparatus or Machines",
    "B05": "Spraying or Atomising; Applying Liquids",
    "B06": "Generating or Transmitting Mechanical Vibrations",
    "B07": "Separating Solids from Solids; Sorting",
    "B08": "Cleaning",
    "B09": "Disposal of Solid Waste; Reclamation",
    "B21": "Mechanical Metal-Working Without Removing Material",
    "B22": "Casting; Powder Metallurgy",
    "B23": "Machine Tools; Metal-Working",
    "B24": "Grinding; Polishing",
    "B25": "Hand Tools; Portable Power-Driven Tools",
    "B26": "Hand Cutting Tools; Cutting; Severing",
    "B27": "Working or Preserving Wood",
    "B28": "Working Cement, Clay, Stone",
    "B29": "Working of Plastics; Working of Substances in Plastic State",
    "B30": "Presses",
    "B31": "Making Paper Articles; Working Paper",
    "B32": "Layered Products",
    "B33": "Additive Manufacturing Technology",
    "B41": "Printing; Lining Machines; Typewriters; Stamps",
    "B42": "Bookbinding; Albums; Filing",
    "B43": "Writing or Drawing Implements",
    "B44": "Decorative Arts",
    "B60": "Vehicles in General",
    "B61": "Railways",
    "B62": "Land Vehicles for Travelling Otherwise Than on Rails",
    "B63": "Ships or Other Waterborne Vessels",
    "B64": "Aircraft; Aviation; Cosmonautics",
    "B65": "Conveying; Packing; Storing; Handling Material",
    "B66": "Hoisting; Lifting; Hauling",
    "B67": "Opening or Closing Bottles, Jars",
    "B68": "Saddlery; Upholstery",
    "B81": "Microstructural Technology",
    "B82": "Nanotechnology",
    # C — Chemistry; Metallurgy
    "C01": "Inorganic Chemistry",
    "C02": "Treatment of Water, Sewage",
    "C03": "Glass; Mineral or Slag Wool",
    "C04": "Cements; Ceramics; Refractories",
    "C05": "Fertilisers; Manufacture Thereof",
    "C06": "Explosives; Matches",
    "C07": "Organic Chemistry",
    "C08": "Organic Macromolecular Compounds; Polymers",
    "C09": "Dyes; Paints; Polishes; Adhesives",
    "C10": "Petroleum, Gas or Coke Industries",
    "C11": "Animal or Vegetable Oils, Fats; Detergents",
    "C12": "Biochemistry; Microbiology; Enzymology",
    "C13": "Sugar Industry",
    "C14": "Skins; Hides; Pelts; Leather",
    "C21": "Metallurgy of Iron",
    "C22": "Metallurgy; Ferrous or Non-Ferrous Alloys",
    "C23": "Coating Metallic Material",
    "C25": "Electrolytic or Electrophoretic Processes",
    "C30": "Crystal Growth",
    "C40": "Combinatorial Technology",
    # D — Textiles; Paper
    "D01": "Natural or Man-Made Threads or Fibres; Spinning",
    "D02": "Yarns; Mechanical Finishing of Yarns or Ropes",
    "D03": "Weaving",
    "D04": "Braiding; Lace-Making; Knitting",
    "D05": "Sewing; Embroidering; Tufting",
    "D06": "Treatment of Textiles; Laundering",
    "D07": "Ropes; Cables Other Than Electric",
    "D21": "Paper-Making; Production of Cellulose",
    # E — Fixed Constructions
    "E01": "Construction of Roads, Railways, Bridges",
    "E02": "Hydraulic Engineering; Foundations; Soil-Shifting",
    "E03": "Water Supply; Sewerage",
    "E04": "Building",
    "E05": "Locks; Keys; Window or Door Fittings",
    "E06": "Doors, Windows, Shutters; Ladders",
    "E21": "Earth Drilling; Mining",
    # F — Mechanical Engineering
    "F01": "Machines or Engines in General",
    "F02": "Combustion Engines",
    "F03": "Machines or Engines for Liquids; Wind/Spring Motors",
    "F04": "Positive-Displacement Machines for Liquids; Pumps",
    "F05": "Indexing Scheme for Engines or Pumps",
    "F15": "Fluid-Pressure Actuators; Hydraulics",
    "F16": "Engineering Elements or Units",
    "F17": "Storing or Distributing Gases or Liquids",
    "F21": "Lighting",
    "F22": "Steam Generation",
    "F23": "Combustion Apparatus; Combustion Processes",
    "F24": "Heating; Ranges; Ventilating",
    "F25": "Refrigeration or Cooling",
    "F26": "Drying",
    "F27": "Furnaces; Kilns; Ovens; Retorts",
    "F28": "Heat Exchange in General",
    "F41": "Weapons",
    "F42": "Ammunition; Blasting",
    # G — Physics
    "G01": "Measuring; Testing",
    "G02": "Optics",
    "G03": "Photography; Cinematography; Holography",
    "G04": "Horology",
    "G05": "Controlling; Regulating",
    "G06": "Computing; Calculating; Counting",
    "G07": "Checking-Devices",
    "G08": "Signalling",
    "G09": "Educating; Cryptography; Display",
    "G10": "Musical Instruments; Acoustics",
    "G11": "Information Storage",
    "G12": "Instrument Details",
    "G16": "Information and Communication Technology (ICT)",
    "G21": "Nuclear Physics; Nuclear Engineering",
    # H — Electricity
    "H01": "Electric Elements",
    "H02": "Generation, Conversion, Distribution of Electric Power",
    "H03": "Electronic Circuitry",
    "H04": "Electric Communication Technique",
    "H05": "Electric Techniques Not Otherwise Provided For",
    "H10": "Semiconductor Devices; Electric Solid-State Devices",
    # Y — Emerging Cross-Sectional Technologies
    "Y02": "Technologies for Climate Change Mitigation",
    "Y04": "Information and Communication Technologies with Impact on Other Technology Areas",
    "Y10": "Technical Subjects Covered by Former USPC",
}


# --- CPC Subklassen (Level 4, z.B. "A61K", "G06N") ---

CPC_SUBCLASS_DESCRIPTIONS: dict[str, str] = {
    # A — Human Necessities
    "A01B": "Soil Working in Agriculture or Forestry",
    "A01C": "Planting; Sowing; Fertilising",
    "A01G": "Horticulture; Cultivation of Vegetables/Fruits",
    "A01H": "New Plants or Processes for Obtaining Them",
    "A01K": "Animal Husbandry; Care of Birds/Fish/Insects",
    "A01N": "Preservation of Bodies; Biocides; Pest Repellants",
    "A23L": "Foods, Foodstuffs; Non-Alcoholic Beverages",
    "A61B": "Diagnosis; Surgery; Identification",
    "A61C": "Dentistry; Dental Prosthetics",
    "A61F": "Filters Implantable; Prostheses; Orthopaedic Devices",
    "A61G": "Transport, Personal Conveyances for Patients",
    "A61H": "Physical Therapy Apparatus",
    "A61J": "Containers for Medical/Pharmaceutical Purposes",
    "A61K": "Preparations for Medical, Dental or Toilet Purposes",
    "A61L": "Methods or Apparatus for Sterilising Materials",
    "A61M": "Devices for Introducing Media into the Body",
    "A61N": "Electrotherapy; Magnetotherapy; Radiation Therapy",
    "A61P": "Therapeutic Activity of Chemical Compounds",
    "A61Q": "Use of Cosmetics or Similar Toilet Preparations",
    # B — Operations; Transport
    "B01D": "Separation",
    "B01F": "Mixing",
    "B01J": "Chemical or Physical Processes; Catalysis",
    "B01L": "Chemical or Physical Laboratory Apparatus",
    "B05B": "Spraying Apparatus",
    "B22F": "Working Metallic Powder; Manufacture of Metal Powder",
    "B23K": "Soldering; Welding; Cutting by Applying Heat",
    "B25J": "Manipulators; Chambers with Manipulation Devices",
    "B29C": "Shaping or Joining of Plastics",
    "B32B": "Layered Products",
    "B33Y": "Additive Manufacturing",
    "B41J": "Typewriters; Selective Printing Mechanisms",
    "B60C": "Vehicle Tyres",
    "B60K": "Arrangement of Propulsion Units in Vehicles",
    "B60L": "Propulsion of Electrically-Propelled Vehicles",
    "B60R": "Vehicles, Vehicle Fittings",
    "B60S": "Servicing, Cleaning, Repairing of Vehicles",
    "B60W": "Conjoint Control of Vehicle Sub-Units",
    "B62D": "Motor Vehicles; Trailers",
    "B64C": "Aeroplanes; Helicopters",
    "B64U": "Unmanned Aerial Vehicles (UAVs)",
    "B65D": "Containers for Storage or Transport",
    "B65G": "Transport or Storage Devices",
    "B82Y": "Specific Uses or Applications of Nanostructures",
    # C — Chemistry; Metallurgy
    "C01B": "Non-Metallic Elements; Compounds Thereof",
    "C01G": "Compounds of Metals",
    "C02F": "Treatment of Water, Waste Water, Sewage",
    "C07C": "Acyclic or Carbocyclic Compounds",
    "C07D": "Heterocyclic Compounds",
    "C07F": "Acyclic/Carbocyclic/Heterocyclic Compounds with Metallic Elements",
    "C07H": "Sugars; Derivatives Thereof; Nucleosides; Nucleotides",
    "C07K": "Peptides",
    "C08G": "Macromolecular Compounds Obtained by Reactions",
    "C08J": "Working-Up; General Processes of Compounding",
    "C08K": "Use of Inorganic or Non-Macromolecular Organic Substances as Compounding Ingredients",
    "C08L": "Compositions of Macromolecular Compounds",
    "C09D": "Coating Compositions; Paints; Inks",
    "C09K": "Materials for Applications Not Otherwise Provided For",
    "C10G": "Cracking Hydrocarbon Oils",
    "C10L": "Fuels Not Otherwise Provided For",
    "C12M": "Apparatus for Enzymology or Microbiology",
    "C12N": "Microorganisms or Enzymes; Compositions Thereof",
    "C12P": "Fermentation or Enzyme-Using Processes",
    "C12Q": "Measuring or Testing Using Enzymes or Microorganisms",
    "C22C": "Alloys",
    "C23C": "Coating Metallic Material; Surface Treatment",
    "C25B": "Electrolytic or Electrophoretic Processes for Production of Compounds",
    "C25D": "Electrolytic or Electrophoretic Coating",
    "C30B": "Single-Crystal Growth",
    # D — Textiles; Paper
    "D01F": "Chemical Features of Artificial Filaments",
    "D06M": "Treatment of Fibres or Filaments from Glass/Minerals/Slags",
    "D21H": "Pulp Compositions; Impregnating or Coating of Paper",
    # E — Fixed Constructions
    "E04B": "General Building Constructions; Walls",
    "E04C": "Structural Elements; Building Materials",
    "E04H": "Buildings for Particular Purposes; Swimming Pools",
    "E21B": "Earth Drilling",
    # F — Mechanical Engineering
    "F01D": "Non-Positive-Displacement Machines or Engines (Turbines)",
    "F01N": "Gas-Flow Silencers or Exhaust Apparatus for Machines",
    "F02D": "Controlling Combustion Engines",
    "F02M": "Supplying Combustion Engines",
    "F03D": "Wind Motors",
    "F04B": "Positive-Displacement Machines for Liquids; Pumps",
    "F16B": "Devices for Fastening or Securing Constructional Elements",
    "F16H": "Gearing",
    "F16K": "Valves; Taps; Cocks",
    "F16L": "Pipes; Joints; Fittings for Pipes",
    "F24D": "Domestic- or Space-Heating Systems",
    "F24F": "Air-Conditioning; Ventilation",
    "F24S": "Solar Heat Collectors",
    "F25B": "Refrigeration Machines, Plants or Systems",
    "F28D": "Heat-Exchange Apparatus",
    "F28F": "Details of Heat-Exchange Apparatus",
    # G — Physics
    "G01B": "Measuring Length, Thickness, Angles",
    "G01C": "Measuring Distances, Levels, Bearings; Surveying",
    "G01J": "Measurement of Intensity, Velocity, Spectral Content of Light",
    "G01K": "Measuring Temperature; Thermometers",
    "G01L": "Measuring Force, Stress, Torque, Work, Mechanical Power",
    "G01N": "Investigating or Analysing Materials by Physical/Chemical Methods",
    "G01R": "Measuring Electric Variables; Measuring Magnetic Variables",
    "G01S": "Radio Direction-Finding; Radar; Navigation",
    "G01T": "Measurement of Nuclear or X-Radiation",
    "G02B": "Optical Elements, Systems or Apparatus",
    "G02F": "Devices or Arrangements for Controlling Light Intensity",
    "G03F": "Photomechanical Production of Textured Surfaces",
    "G05B": "Control or Regulating Systems in General",
    "G05D": "Systems for Controlling Non-Electric Variables",
    "G06F": "Electric Digital Data Processing",
    "G06K": "Graphical Data Reading; Presentation of Data",
    "G06N": "Computing Arrangements Based on Specific Computational Models",
    "G06Q": "Data Processing Systems for Administrative/Financial Purposes",
    "G06T": "Image Data Processing or Generation",
    "G06V": "Image or Video Recognition or Understanding",
    "G08B": "Signalling or Calling Systems",
    "G08G": "Traffic Control Systems",
    "G09B": "Educational or Demonstration Appliances",
    "G09G": "Arrangements for Control of Display Devices",
    "G10L": "Speech Analysis or Synthesis; Speech Recognition",
    "G11B": "Information Storage Based on Relative Movement",
    "G11C": "Static Stores",
    "G16B": "Bioinformatics",
    "G16C": "Computational Chemistry; Chemoinformatics",
    "G16H": "Healthcare Informatics",
    "G16Y": "Information and Communication Technology for Internet of Things (IoT)",
    "G21B": "Fusion Reactors",
    "G21C": "Nuclear Reactors",
    # H — Electricity
    "H01B": "Cables; Conductors; Insulators",
    "H01F": "Magnets; Inductances; Transformers",
    "H01G": "Capacitors; Capacitors, Rectifiers, Detectors",
    "H01H": "Electric Switches; Relays; Selectors",
    "H01J": "Electric Discharge Tubes or Discharge Lamps",
    "H01L": "Semiconductor Devices; Electric Solid-State Devices",
    "H01M": "Processes or Means for Direct Conversion of Chemical Energy into Electrical Energy",
    "H01P": "Waveguides; Resonators, Lines",
    "H01Q": "Antennas",
    "H01R": "Electrically-Conductive Connections",
    "H01S": "Devices Using Stimulated Emission (Lasers)",
    "H02G": "Installation of Electric Cables or Lines",
    "H02H": "Emergency Protective Circuit Arrangements",
    "H02J": "Circuit Arrangements for Supplying or Distributing Electric Power",
    "H02K": "Dynamo-Electric Machines",
    "H02M": "Apparatus for Conversion Between AC and AC, or AC and DC",
    "H02N": "Electric Machines Not Otherwise Provided For",
    "H02P": "Control or Regulation of Electric Motors",
    "H02S": "Generation of Electric Power by Conversion of IR/Light/UV (Photovoltaics)",
    "H03H": "Impedance Networks (Filters, Resonators)",
    "H03K": "Pulse Technique",
    "H03M": "Coding; Decoding; Code Conversion",
    "H04B": "Transmission",
    "H04J": "Multiplex Communication",
    "H04L": "Transmission of Digital Information",
    "H04M": "Telephonic Communication",
    "H04N": "Pictorial Communication (Television)",
    "H04Q": "Selecting",
    "H04R": "Loudspeakers; Microphones; Headphones",
    "H04S": "Stereophonic Systems",
    "H04W": "Wireless Communication Networks",
    "H05B": "Electric Heating; Electric Lighting Not Otherwise Provided For",
    "H05K": "Printed Circuits; Casings for Electric Apparatus",
    "H10B": "Electronic Memory Devices",
    "H10K": "Organic Electric Solid-State Devices",
    "H10N": "Electric Solid-State Devices Not Otherwise Provided For",
    # Y — Emerging Technologies
    "Y02A": "Technologies for Adaptation to Climate Change",
    "Y02B": "Climate Change Mitigation — Buildings",
    "Y02C": "Capture, Storage, Sequestration of GHG",
    "Y02D": "Climate Change Mitigation — ICT",
    "Y02E": "Reduction of GHG Emissions — Energy Generation/Transmission/Distribution",
    "Y02P": "Climate Change Mitigation — Goods Production/Processing",
    "Y02T": "Climate Change Mitigation — Transportation",
    "Y02W": "Climate Change Mitigation — Wastewater Treatment/Waste Management",
    "Y04S": "Systems Integrating Technologies Related to Power Network Operation",
    "Y10S": "Technical Subjects Covered by Former USPC Cross-Reference Art Collections",
    "Y10T": "Technical Subjects Covered by Former US Classification",
}


def describe_cpc(code: str) -> str:
    """CPC-Code beschreiben.

    Versucht Subclass (4 Zeichen) → Class (3 Zeichen) → Section (1 Zeichen).
    Gibt Leerstring zurueck wenn nichts gefunden.

    Args:
        code: CPC-Code (z.B. "G06N", "H01L33/00", "G06")

    Returns:
        Beschreibung oder Leerstring
    """
    if not code:
        return ""

    clean = code.strip()

    # Subclass (Level 4): z.B. "G06N"
    if len(clean) >= 4:
        sub = clean[:4]
        if sub in CPC_SUBCLASS_DESCRIPTIONS:
            return CPC_SUBCLASS_DESCRIPTIONS[sub]

    # Class (Level 3): z.B. "G06"
    if len(clean) >= 3:
        cls = clean[:3]
        if cls in CPC_CLASS_DESCRIPTIONS:
            return CPC_CLASS_DESCRIPTIONS[cls]

    # Section (Level 1): z.B. "G"
    if len(clean) >= 1:
        sec = clean[0]
        if sec in CPC_SECTION_DESCRIPTIONS:
            return CPC_SECTION_DESCRIPTIONS[sec]

    return ""


# Alias fuer Rueckwaertskompatibilitaet (UC5 service.py importiert get_cpc_description)
get_cpc_description = describe_cpc
