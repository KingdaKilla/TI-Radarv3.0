"""
Extract individual schema PNGs from the full ERM diagram.
Each crop includes the schema box PLUS outgoing connectors with their labels.
No artificial text overlay — just the original diagram content.
"""
from PIL import Image
import os

SRC = r"C:\Users\bensc\OneDrive\HWR\6. Semester\Bachelor\07_Prototypen\mvp_v3.0_new\docs\diagrams\erm_ti_radar.png"
OUT_DIR = r"C:\Users\bensc\OneDrive\HWR\6. Semester\Bachelor\07_Prototypen\mvp_v3.0_new\docs\diagrams\schemas"
os.makedirs(OUT_DIR, exist_ok=True)

img = Image.open(SRC)
W, H = img.size
print(f"Source: {W}x{H}")

# Exact schema box boundaries (from color detection):
# patent_schema:   (1582, 2836) - (4467, 5297)
# cordis_schema:   (6266, 2838) - (8985, 5295)
# research_schema: (7156,  120) - (9703, 2145)
# entity_schema:   (5964, 6308) - (7595, 8313)
# cross_schema:    ( 120, 5775) - (5927, 7095)
# export_schema:   (7632, 6308) - (9345, 8457)
#
# Connectors run in the space BETWEEN schemas.
# We expand each crop to capture half the gap toward connected schemas,
# so the connector labels are included.

# Crop areas: (left, top, right, bottom) in pixels
# Each includes the schema box + extended margin toward connected schemas
CROPS = {
    "patent_schema": (
        # left: image edge (small margin)
        100,
        # top: extend up toward area where connector labels may be
        2400,
        # right: extend toward cordis (connector labels in the gap)
        5400,
        # bottom: extend down toward cross_schema connectors + labels
        6200,
    ),
    "cordis_schema": (
        # left: extend to capture connector to entity/cross + labels
        5200,
        # top: extend up to capture DOI-Match connector from research
        2000,
        # right: image edge
        9750,
        # bottom: extend down toward entity/export connectors + labels
        6200,
    ),
    "research_schema": (
        # left: some margin
        6500,
        # top: image edge
        50,
        # right: image edge
        9780,
        # bottom: extend down to capture DOI-match + export connectors
        2800,
    ),
    "entity_schema": (
        # left: extend to capture incoming connector labels
        4800,
        # top: extend up to capture connector labels from patent/cordis
        5800,
        # right: extend a bit
        7700,
        # bottom: image edge
        8500,
    ),
    "cross_schema": (
        # left: image edge
        50,
        # top: extend up to capture "patents materialized" label
        5200,
        # right: extend to capture connector labels
        6200,
        # bottom: margin
        7200,
    ),
    "export_schema": (
        # left: extend to capture incoming connector labels
        7000,
        # top: extend up to capture connector labels
        5800,
        # right: image edge
        9750,
        # bottom: image edge
        8530,
    ),
}

for name, (l, t, r, b) in CROPS.items():
    # Clamp to image bounds
    l = max(0, l)
    t = max(0, t)
    r = min(W, r)
    b = min(H, b)

    cropped = img.crop((l, t, r, b))
    out_path = os.path.join(OUT_DIR, f"{name}.png")
    cropped.save(out_path, "PNG")
    print(f"  {name}: {cropped.size[0]}x{cropped.size[1]} -> {out_path}")

print(f"\nDone. {len(CROPS)} schema PNGs in {OUT_DIR}")
