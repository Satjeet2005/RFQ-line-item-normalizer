"""
Generator for the 100-item synthetic product catalog.
Generates data/catalog.json ensuring all specifications from PRD Section J & I are satisfied.
"""
import json
from pathlib import Path

def create_catalog():
    products = []

    # 1. GI Pipes (16 products)
    gi_pipe_sizes = ["15", "20", "25", "32", "40", "50", "80", "100"]
    gi_classes = ["A", "B"]
    idx = 1
    for size in gi_pipe_sizes:
        for cls in gi_classes:
            inch_map = {
                "15": "1/2 inch", "20": "3/4 inch", "25": "1 inch",
                "32": "1-1/4 inch", "40": "1-1/2 inch", "50": "2 inch",
                "80": "3 inch", "100": "4 inch"
            }
            inch_label = inch_map[size]
            class_name = "Light" if cls == "A" else "Medium"
            sku = f"PIPE-{idx:03d}"
            name = f"GI Pipe {size}mm Class {cls}"
            aliases = [
                f"Galvanized Iron Pipe {size}mm {class_name}",
                f"GI Pipe {inch_label} Class {cls}"
            ]
            products.append({
                "sku": sku,
                "name": name,
                "category": "pipe",
                "uom": "mtr",
                "attributes": {
                    "material": "GI",
                    "size_mm": size,
                    "class": cls
                },
                "aliases": aliases
            })
            idx += 1

    # 2. PVC Pipes (12 products)
    pvc_pipe_sizes = ["20", "25", "32", "40", "50", "75"]
    pvc_classes = ["A", "B"]
    for size in pvc_pipe_sizes:
        for cls in pvc_classes:
            sku = f"PIPE-{idx:03d}"
            name = f"PVC Pipe {size}mm Class {cls}"
            aliases = [
                f"UPVC Conduit Pipe {size}mm Class {cls}",
                f"Rigid PVC Pipe {size}mm"
            ]
            products.append({
                "sku": sku,
                "name": name,
                "category": "pipe",
                "uom": "mtr",
                "attributes": {
                    "material": "PVC",
                    "size_mm": size,
                    "class": cls
                },
                "aliases": aliases
            })
            idx += 1

    # 3. Fasteners - MS Hex Bolts Grade 4.6 (12 products)
    bolt_idx = 1
    ms_46_bolts = [
        ("M6", "25"), ("M6", "40"),
        ("M8", "30"), ("M8", "50"),
        ("M10", "40"), ("M10", "60"),
        ("M12", "50"), ("M12", "75"),
        ("M16", "60"), ("M16", "100"),
        ("M20", "75"), ("M20", "100")
    ]
    for thread, length in ms_46_bolts:
        sku = f"BOLT-{bolt_idx:03d}"
        name = f"MS Hex Bolt {thread}x{length} Grade 4.6"
        aliases = [
            f"Mild Steel Hex Bolt {thread}*{length} Gr 4.6",
            f"MS Hexagon Head Bolt {thread} x {length}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fastener",
            "uom": "nos",
            "attributes": {
                "material": "MS",
                "thread": thread,
                "length_mm": length,
                "grade": "4.6"
            },
            "aliases": aliases
        })
        bolt_idx += 1

    # 4. Fasteners - MS Hex Bolts Grade 8.8 (8 products, near-duplicates)
    ms_88_bolts = [
        ("M8", "50"),
        ("M10", "40"), ("M10", "60"),
        ("M12", "50"), ("M12", "75"),
        ("M16", "60"), ("M16", "100"),
        ("M20", "75")
    ]
    for thread, length in ms_88_bolts:
        sku = f"BOLT-{bolt_idx:03d}"
        name = f"MS Hex Bolt {thread}x{length} Grade 8.8"
        aliases = [
            f"High Tensile Hex Bolt {thread}x{length} 8.8",
            f"HT Hex Bolt {thread}*{length} Gr 8.8"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fastener",
            "uom": "nos",
            "attributes": {
                "material": "MS",
                "thread": thread,
                "length_mm": length,
                "grade": "8.8"
            },
            "aliases": aliases
        })
        bolt_idx += 1

    # 5. Fasteners - SS304 Hex Bolts (6 products)
    ss_bolts = [
        ("M8", "30"), ("M8", "50"),
        ("M10", "40"), ("M10", "60"),
        ("M12", "50"),
        ("M16", "60")
    ]
    for thread, length in ss_bolts:
        sku = f"BOLT-{bolt_idx:03d}"
        name = f"SS304 Hex Bolt {thread}x{length}"
        aliases = [
            f"Stainless Steel Hex Bolt {thread}x{length} SS 304",
            f"SS 304 Bolt {thread}*{length}"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fastener",
            "uom": "nos",
            "attributes": {
                "material": "SS304",
                "thread": thread,
                "length_mm": length
            },
            "aliases": aliases
        })
        bolt_idx += 1

    # 6. Fasteners - Hex Nuts (6 products)
    nuts = ["M6", "M8", "M10", "M12", "M16", "M20"]
    for thread in nuts:
        sku = f"BOLT-{bolt_idx:03d}"
        name = f"MS Hex Nut {thread}"
        aliases = [
            f"Mild Steel Hexagon Nut {thread}",
            f"MS Nut {thread}"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fastener",
            "uom": "nos",
            "attributes": {
                "material": "MS",
                "thread": thread
            },
            "aliases": aliases
        })
        bolt_idx += 1

    # 7. Fasteners - Plain Washers (4 products)
    washers = [
        ("M8", "8"),
        ("M10", "10"),
        ("M12", "12"),
        ("M16", "16")
    ]
    for thread, size in washers:
        sku = f"BOLT-{bolt_idx:03d}"
        name = f"MS Plain Washer {thread}"
        aliases = [
            f"Mild Steel Flat Washer {thread}",
            f"MS Washer ID {size}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fastener",
            "uom": "nos",
            "attributes": {
                "material": "MS",
                "size_mm": size
            },
            "aliases": aliases
        })
        bolt_idx += 1

    # 8. Fittings - GI 90 Deg Elbows (5 products)
    fitt_idx = 1
    gi_elbow_sizes = ["15", "20", "25", "32", "50"]
    for size in gi_elbow_sizes:
        sku = f"FITT-{fitt_idx:03d}"
        name = f"GI 90 Degree Elbow {size}mm Class B"
        aliases = [
            f"Galvanized Iron Elbow 90 Deg {size}mm",
            f"GI Bend 90 {size}mm Medium"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fitting",
            "uom": "nos",
            "attributes": {
                "material": "GI",
                "size_mm": size,
                "class": "B"
            },
            "aliases": aliases
        })
        fitt_idx += 1

    # 9. Fittings - GI Equal Tees (4 products)
    gi_tee_sizes = ["15", "20", "25", "50"]
    for size in gi_tee_sizes:
        sku = f"FITT-{fitt_idx:03d}"
        name = f"GI Equal Tee {size}mm Class B"
        aliases = [
            f"Galvanized Iron Equal Tee {size}mm",
            f"GI Tee {size}mm Medium"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fitting",
            "uom": "nos",
            "attributes": {
                "material": "GI",
                "size_mm": size,
                "class": "B"
            },
            "aliases": aliases
        })
        fitt_idx += 1

    # 10. Fittings - GI Sockets (4 products)
    gi_socket_sizes = ["15", "20", "25", "50"]
    for size in gi_socket_sizes:
        sku = f"FITT-{fitt_idx:03d}"
        name = f"GI Socket Coupling {size}mm Class B"
        aliases = [
            f"Galvanized Iron Pipe Socket {size}mm",
            f"GI Coupling {size}mm Medium"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fitting",
            "uom": "nos",
            "attributes": {
                "material": "GI",
                "size_mm": size,
                "class": "B"
            },
            "aliases": aliases
        })
        fitt_idx += 1

    # 11. Fittings - PVC 90 Deg Elbows (5 products)
    pvc_elbow_sizes = ["20", "25", "32", "40", "50"]
    for size in pvc_elbow_sizes:
        sku = f"FITT-{fitt_idx:03d}"
        name = f"PVC 90 Degree Elbow {size}mm"
        aliases = [
            f"UPVC Conduit Elbow 90 {size}mm",
            f"PVC Pipe Bend {size}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "fitting",
            "uom": "nos",
            "attributes": {
                "material": "PVC",
                "size_mm": size
            },
            "aliases": aliases
        })
        fitt_idx += 1

    # 12. Valves - Brass Ball Valves (4 products)
    valv_idx = 1
    ball_valve_sizes = ["15", "20", "25", "50"]
    for size in ball_valve_sizes:
        sku = f"VALV-{valv_idx:03d}"
        name = f"Brass Ball Valve Screwed {size}mm"
        aliases = [
            f"Brass Screwed Ball Valve {size}mm",
            f"Forged Brass Ball Valve {size}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "valve",
            "uom": "nos",
            "attributes": {
                "material": "BRASS",
                "size_mm": size
            },
            "aliases": aliases
        })
        valv_idx += 1

    # 13. Valves - Brass Gate Valves (4 products)
    gate_valve_sizes = ["15", "20", "25", "50"]
    for size in gate_valve_sizes:
        sku = f"VALV-{valv_idx:03d}"
        name = f"Brass Gate Valve Screwed {size}mm"
        aliases = [
            f"Brass Peet Valve Screwed {size}mm",
            f"Brass Sluice Gate Valve {size}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "valve",
            "uom": "nos",
            "attributes": {
                "material": "BRASS",
                "size_mm": size
            },
            "aliases": aliases
        })
        valv_idx += 1

    # 14. Valves - GI Check Valves (2 products)
    gi_check_sizes = ["25", "50"]
    for size in gi_check_sizes:
        sku = f"VALV-{valv_idx:03d}"
        name = f"GI Non Return Check Valve {size}mm"
        aliases = [
            f"Galvanized Iron NRV Valve {size}mm",
            f"GI Check Valve Screwed {size}mm"
        ]
        products.append({
            "sku": sku,
            "name": name,
            "category": "valve",
            "uom": "nos",
            "attributes": {
                "material": "GI",
                "size_mm": size
            },
            "aliases": aliases
        })
        valv_idx += 1

    # 15. Consumables (8 products)
    consumables = [
        {
            "sku": "CONS-001",
            "name": "Welding Electrodes MS E6013 3.15mm",
            "category": "consumable",
            "uom": "kg",
            "attributes": {"material": "MS", "size_mm": "3.15"},
            "aliases": ["Mild Steel Welding Rod 3.15mm", "Arc Welding Electrodes 3.15"]
        },
        {
            "sku": "CONS-002",
            "name": "Welding Electrodes MS E6013 4.0mm",
            "category": "consumable",
            "uom": "kg",
            "attributes": {"material": "MS", "size_mm": "4"},
            "aliases": ["Mild Steel Welding Rod 4mm", "Arc Welding Electrodes 4.0"]
        },
        {
            "sku": "CONS-003",
            "name": "PTFE Thread Seal Tape 12mm x 10m",
            "category": "consumable",
            "uom": "roll",
            "attributes": {"size_mm": "12"},
            "aliases": ["Teflon Thread Tape 12mm", "PTFE Pipe Joint Tape"]
        },
        {
            "sku": "CONS-004",
            "name": "Red Oxide Metal Primer Paint",
            "category": "consumable",
            "uom": "ltr",
            "attributes": {},
            "aliases": ["Anti Corrosive Red Oxide Primer", "Industrial Red Oxide Paint"]
        },
        {
            "sku": "CONS-005",
            "name": "Industrial Synthetic Enamel Paint Gloss Black",
            "category": "consumable",
            "uom": "ltr",
            "attributes": {},
            "aliases": ["Synthetic Enamel Black Paint", "Gloss Black Machinery Paint"]
        },
        {
            "sku": "CONS-006",
            "name": "GI Binding Wire 16 SWG 1.6mm",
            "category": "consumable",
            "uom": "kg",
            "attributes": {"material": "GI", "size_mm": "1.6"},
            "aliases": ["Galvanized Iron Tying Wire 16 Gauge", "GI Tie Wire 1.6mm"]
        },
        {
            "sku": "CONS-007",
            "name": "Multi Purpose Grease Compound",
            "category": "consumable",
            "uom": "g",
            "attributes": {},
            "aliases": ["Lithium Base Industrial Grease", "Bearing Grease Compound"]
        },
        {
            "sku": "CONS-008",
            "name": "High Strength Non Shrink Structural Grout",
            "category": "consumable",
            "uom": "bag",
            "attributes": {},
            "aliases": ["Cementitious Non Shrink Grout 25kg", "Precision Machine Grout Compound"]
        }
    ]
    products.extend(consumables)

    return products

if __name__ == "__main__":
    catalog = create_catalog()
    out_path = Path("/home/satjeet/Desktop/isocode/data/catalog.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(catalog)} products in {out_path}")
