"""
Automated catalog validation script.
Validates data/catalog.json against PRD constraints and schemas.
"""
import json
import re
import sys
from pathlib import Path
from decimal import Decimal

SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3}$")
THREAD_PATTERN = re.compile(r"^M\d+$")
VALID_MATERIALS = {"GI", "MS", "SS304", "SS316", "PVC", "BRASS", "CU"}
VALID_CLASSES = {"A", "B", "C"}
VALID_GRADES = {"4.6", "8.8", "10.9"}
VALID_UOMS = {"nos", "set", "pair", "box", "roll", "bag", "mtr", "ft", "kg", "g", "ltr", "ml"}
ALLOWED_ATTR_KEYS = {"size_mm", "length_mm", "thread", "material", "class", "grade"}
FORBIDDEN_PRICE_WORDS = {"price", "cost", "rate", "mrp", "currency", "amount"}

def validate_catalog(catalog_path: Path):
    errors = []
    if not catalog_path.exists():
        return [f"Catalog file not found: {catalog_path}"]

    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON: {e}"]

    if not isinstance(data, list):
        return ["Catalog root must be a JSON array"]

    sku_set = set()
    name_set = set()

    for idx, item in enumerate(data):
        prefix = f"Item #{idx}"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: Item must be a JSON object")
            continue

        # Check for forbidden price fields
        for k in item.keys():
            if k.lower() in FORBIDDEN_PRICE_WORDS:
                errors.append(f"{prefix}: Forbidden price field found: '{k}'")

        sku = item.get("sku")
        if not sku or not isinstance(sku, str):
            errors.append(f"{prefix}: Missing or non-string SKU")
        else:
            prefix = f"Item {sku}"
            if not SKU_PATTERN.match(sku):
                errors.append(f"{prefix}: SKU '{sku}' does not match pattern [A-Z]{{2,4}}-\\d{{3}}")
            if sku in sku_set:
                errors.append(f"{prefix}: Duplicate SKU '{sku}'")
            sku_set.add(sku)

        name = item.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}: Missing or invalid name")
        else:
            if name in name_set:
                errors.append(f"{prefix}: Duplicate exact product name '{name}'")
            name_set.add(name)

        category = item.get("category")
        if not category or not isinstance(category, str):
            errors.append(f"{prefix}: Missing or invalid category")

        uom = item.get("uom")
        if uom not in VALID_UOMS:
            errors.append(f"{prefix}: Invalid UOM '{uom}', must be one of {sorted(VALID_UOMS)}")

        # Attributes validation
        attrs = item.get("attributes")
        if not isinstance(attrs, dict):
            errors.append(f"{prefix}: 'attributes' must be a JSON object")
        else:
            for k, v in attrs.items():
                if k not in ALLOWED_ATTR_KEYS:
                    errors.append(f"{prefix}: Disallowed attribute key '{k}'")
                    continue
                if not isinstance(v, str):
                    errors.append(f"{prefix}: Attribute '{k}' value must be string, got {type(v).__name__}")
                    continue

                if k in ("size_mm", "length_mm"):
                    try:
                        d = Decimal(v)
                        # Check canonical: no trailing zeros after decimal point unless necessary, or integer
                        if "." in v:
                            normalized = str(d.normalize())
                            # Python normalize for 10.0 -> 1E+1 or 10
                            if v.endswith("0") or v.endswith("."):
                                errors.append(f"{prefix}: Decimal string '{v}' for '{k}' must not have trailing zeros")
                    except Exception:
                        errors.append(f"{prefix}: Attribute '{k}' value '{v}' is not a valid Decimal string")

                elif k == "thread":
                    if not THREAD_PATTERN.match(v):
                        errors.append(f"{prefix}: Thread '{v}' does not match pattern M<d>")

                elif k == "material":
                    if v not in VALID_MATERIALS:
                        errors.append(f"{prefix}: Material '{v}' not in {sorted(VALID_MATERIALS)}")

                elif k == "class":
                    if v not in VALID_CLASSES:
                        errors.append(f"{prefix}: Class '{v}' not in {sorted(VALID_CLASSES)}")

                elif k == "grade":
                    if v not in VALID_GRADES:
                        errors.append(f"{prefix}: Grade '{v}' not in {sorted(VALID_GRADES)}")

        # Aliases validation
        aliases = item.get("aliases")
        if not isinstance(aliases, list):
            errors.append(f"{prefix}: 'aliases' must be a list")
        else:
            if len(aliases) > 3:
                errors.append(f"{prefix}: Max 3 aliases allowed, got {len(aliases)}")
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    errors.append(f"{prefix}: Alias must be a non-empty string")

    # Sibling distinction check:
    # Within each product family, items that are siblings must differ in at least one declared attribute.
    def get_family(prod):
        n = prod.get("name", "").lower()
        if "pipe" in n:
            return ("pipe", prod.get("attributes", {}).get("material"))
        if "bolt" in n:
            return ("bolt",)
        if "nut" in n:
            return ("nut",)
        if "washer" in n:
            return ("washer",)
        if "elbow" in n:
            return ("elbow", prod.get("attributes", {}).get("material"))
        if "tee" in n:
            return ("tee", prod.get("attributes", {}).get("material"))
        if "socket" in n:
            return ("socket", prod.get("attributes", {}).get("material"))
        if "ball valve" in n:
            return ("ball_valve",)
        if "gate valve" in n:
            return ("gate_valve",)
        if "check valve" in n or "return" in n:
            return ("check_valve",)
        if prod.get("category") == "consumable":
            return (prod.get("sku"),)
        return (prod.get("category"), n)

    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            p1 = data[i]
            p2 = data[j]
            fam1 = get_family(p1)
            fam2 = get_family(p2)
            if fam1 == fam2:
                if p1.get("attributes") == p2.get("attributes") and p1.get("uom") == p2.get("uom"):
                    errors.append(f"Sibling conflict: {p1.get('sku')} and {p2.get('sku')} in family {fam1} have identical attributes {p1.get('attributes')}")

    return errors

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/catalog.json")
    errs = validate_catalog(path)
    if errs:
        print(f"Catalog validation FAILED ({len(errs)} errors):")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"Catalog validation PASSED: {path} is valid.")
