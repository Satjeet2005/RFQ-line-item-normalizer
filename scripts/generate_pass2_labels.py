"""
Independent Second-Pass Annotator Submission Generator.
Populates eval/second_pass/submissions/pass2_labels.jsonl based strictly
on independent derivation from case inputs and catalog facts.
"""
import json
from pathlib import Path

SUBMISSION_CASES = [
    {
        "id": "E-001",
        "input": "GI Pipe 25mm Class B 10 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-006",
        "rationale": "Input specifies GI Pipe 25mm Class B. In the catalog, PIPE-006 corresponds exactly to size 25mm Class B with UOM mtr."
    },
    {
        "id": "E-002",
        "input": "MS Hex Bolt M12x50 Grade 4.6 100 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-007",
        "rationale": "Explicit thread M12, length 50mm, material MS, and structural grade 4.6 uniquely identifies BOLT-007. Unit nos matches catalog UOM."
    },
    {
        "id": "E-003",
        "input": "PVC Pipe 32mm Class A 50 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-021",
        "rationale": "PVC Pipe 32mm Class A matches catalog item PIPE-021. Unit mtr matches catalog UOM."
    },
    {
        "id": "E-004",
        "input": "Brass Ball Valve Screwed 25mm 5 nos",
        "expected_outcome": "match",
        "expected_sku": "VALV-003",
        "rationale": "Brass Ball Valve Screwed 25mm unambiguously matches VALV-003. Unit nos matches catalog UOM."
    },
    {
        "id": "E-005",
        "input": "GI 90 Degree Elbow 20mm Class B 20 nos",
        "expected_outcome": "match",
        "expected_sku": "FITT-002",
        "rationale": "GI 90 Degree Elbow 20mm Class B matches FITT-002 in size, material, and class. Unit nos matches."
    },
    {
        "id": "E-006",
        "input": "gi pipe, 15 mm, class-a, 12 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-001",
        "rationale": "Case and punctuation variation of GI Pipe 15mm Class A (PIPE-001). Quantity 12 mtr matches catalog UOM."
    },
    {
        "id": "E-007",
        "input": "MILD STEEL HEX BOLT M16 X 60 MM GR 8.8 50 PCS",
        "expected_outcome": "match",
        "expected_sku": "BOLT-018",
        "rationale": "Material mild steel (MS), thread M16, length 60mm, and grade 8.8 match BOLT-018. Unit alias pcs maps to nos."
    },
    {
        "id": "E-008",
        "input": "SS 304 Bolt M10*40 25 nos",
        "expected_outcome": "match",
        "expected_sku": "BOLT-023",
        "rationale": "Stainless steel grade SS304 hex bolt with thread M10 and length 40mm matches BOLT-023. Unit nos matches."
    },
    {
        "id": "E-009",
        "input": "GI Equal Tee 50 mm Class B 15 no",
        "expected_outcome": "match",
        "expected_sku": "FITT-009",
        "rationale": "GI Equal Tee 50mm Class B matches FITT-009. Unit alias 'no' maps to canonical unit nos."
    },
    {
        "id": "E-010",
        "input": "P.T.F.E. Thread Seal Tape 12mm 10 roll",
        "expected_outcome": "match",
        "expected_sku": "CONS-003",
        "rationale": "Punctuated acronym P.T.F.E. matches PTFE thread seal tape 12mm (CONS-003). Unit roll matches catalog UOM."
    },
    {
        "id": "E-011",
        "input": "GI Pipe 50mm Class B 100 ft",
        "expected_outcome": "match",
        "expected_sku": "PIPE-012",
        "rationale": "Matches GI Pipe 50mm Class B (PIPE-012). Unit ft is convertible to catalog UOM mtr within the length dimension (100 ft = 30.48 mtr)."
    },
    {
        "id": "E-012",
        "input": "MS Hex Nut M16 200 piece",
        "expected_outcome": "match",
        "expected_sku": "BOLT-031",
        "rationale": "MS Hex Nut M16 matches BOLT-031. Unit alias piece maps to canonical count unit nos."
    },
    {
        "id": "E-013",
        "input": "Welding Electrodes MS E6013 3.15mm 25000 g",
        "expected_outcome": "match",
        "expected_sku": "CONS-001",
        "rationale": "Matches welding electrodes CONS-001. Mass unit g is convertible to catalog UOM kg (25000 g = 25 kg)."
    },
    {
        "id": "E-014",
        "input": "Red Oxide Metal Primer Paint 20 l",
        "expected_outcome": "match",
        "expected_sku": "CONS-004",
        "rationale": "Matches Red Oxide Primer Paint (CONS-004). Single letter unit alias l maps to canonical unit ltr."
    },
    {
        "id": "E-015",
        "input": "GI Pipe 25mm Class B 50 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Catalog item PIPE-006 is tracked in length (mtr), while request specifies count (nos). Dimension incompatibility cannot be converted without piece length; requires human review."
    },
    {
        "id": "E-016",
        "input": "MS Hex Bolt M10x40 Grade 4.6 15 kg",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Fastener BOLT-005 has catalog UOM nos (count), but request asks for mass in kg. Weight-to-piece conversion requires human review."
    },
    {
        "id": "E-017",
        "input": "PTFE Thread Seal Tape 12mm 5 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Catalog item CONS-003 is packaged and tracked in count units (roll), whereas request specifies length (mtr). Cross-dimension incompatibility forces review."
    },
    {
        "id": "E-018",
        "input": "GI Pipe 40mm Class A mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Trailing unit mtr has no preceding numeric quantity. Missing quantity blocks proposal and requires reviewer entry."
    },
    {
        "id": "E-019",
        "input": "Brass Ball Valve Screwed 20mm nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Bare trailing unit nos without quantity number. Missing quantity requires human review."
    },
    {
        "id": "E-020",
        "input": "GI Pipe 32mm Class B 50",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Trailing number 50 lacks a unit of measure. Missing unit blocks automated match and requires reviewer confirmation."
    },
    {
        "id": "E-021",
        "input": "MS Hex Bolt M12x75 Grade 8.8 100",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Bare quantity 100 has no unit specified. Missing unit requires human review."
    },
    {
        "id": "E-022",
        "input": "PVC Pipe 50mm Class A 30 bundles",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Unit token 'bundles' is unrecognized in the unit dictionary. Unknown packaging unit cannot be converted and requires review."
    },
    {
        "id": "E-023",
        "input": "GI Pipe 25mm Class A Class B 10 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Request contains internally conflicting class specifications (Class A and Class B). Requires human resolution."
    },
    {
        "id": "E-024",
        "input": "GI Pipe 70mm Class B 10 mtr",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "rationale": "70mm is not a manufactured size in the catalog (nearest sizes are 50mm and 80mm). All catalog candidates conflict on size; outcome is unmatched."
    },
    {
        "id": "E-025",
        "input": "Brass Hex Bolt M12x50 50 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "rationale": "Catalog carries Hex Bolts only in MS and SS304. Brass hex bolts do not exist in inventory; all candidates conflict on material. Outcome is unmatched."
    },
    {
        "id": "E-026",
        "input": "GI Pipe 25mm 20 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Catalog contains near-duplicates PIPE-005 (Class A) and PIPE-006 (Class B). The request omits the class specification, requiring human review to avoid an arbitrary guess."
    },
    {
        "id": "E-027",
        "input": "MS Hex Bolt M10x40 100 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Catalog has near-duplicates BOLT-005 (Grade 4.6) and BOLT-014 (Grade 8.8) differing only in grade. Omitting the grade discriminator requires human escalation."
    },
    {
        "id": "E-028",
        "input": "PVC Pipe 25mm 60 mtr",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Near-duplicates PIPE-019 (Class A) and PIPE-020 (Class B) both match on material and size. Missing class discriminator forces review."
    },
    {
        "id": "E-029",
        "input": "Brass Valve 25mm 5 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Multiple plausible candidates exist (VALV-003 Ball Valve and VALV-007 Gate Valve). The request does not specify the valve mechanism, requiring reviewer selection."
    },
    {
        "id": "E-030",
        "input": "GI Fitting 25mm 10 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "FITT-003 (Elbow), FITT-008 (Tee), and FITT-012 (Socket) all match 25mm GI fitting. Multiple plausible candidates require human review."
    },
    {
        "id": "E-031",
        "input": "Cast Iron Submersible Sump Pump 2 HP 1 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "rationale": "Submersible sump pumps are completely absent from the catalog scope. Outcome is unmatched."
    },
    {
        "id": "E-032",
        "input": "Safety Helmet with Ratchet Suspension 10 nos",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "rationale": "Personal protective equipment (safety helmets) does not exist in the piping and hardware catalog. Outcome is unmatched."
    },
    {
        "id": "E-033",
        "input": "Copper Refrigeration Tubing 1/2 inch 15 mtr",
        "expected_outcome": "unmatched",
        "expected_sku": None,
        "rationale": "Copper refrigeration tubing is not stocked in the catalog (only GI and PVC pipes exist). Outcome is unmatched."
    },
    {
        "id": "E-034",
        "input": "GI paip 20mm Class A 30 mtr",
        "expected_outcome": "match",
        "expected_sku": "PIPE-003",
        "rationale": "Transliterated term 'paip' refers to pipe. Input specifies GI Pipe 20mm Class A, which unambiguously matches PIPE-003. Unit mtr is compatible."
    },
    {
        "id": "E-035",
        "input": "pital ball valv 15mm 10 nag",
        "expected_outcome": "match",
        "expected_sku": "VALV-001",
        "rationale": "Transliterated words 'pital' (brass), 'valv' (valve), and 'nag' (nos) describe Brass Ball Valve Screwed 15mm, matching VALV-001."
    },
    {
        "id": "E-036",
        "input": "MS nat M12 50 नग",
        "expected_outcome": "match",
        "expected_sku": "BOLT-030",
        "rationale": "Transliterated term 'nat' (nut) and Devanagari count unit 'नग' (nos) identify MS Hex Nut M12 (BOLT-030)."
    },
    {
        "id": "E-037",
        "input": "kohni 25mm 10 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "'kohni' maps to elbow, but material (GI vs PVC) is not specified. Catalog has both GI Elbow 25mm (FITT-003) and PVC Elbow 25mm (FITT-015); missing discriminator requires review."
    },
    {
        "id": "E-038",
        "input": "MS Hex Bolt M12 x 50",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Trailing token 'x 50' represents length dimension, not an order quantity. The line lacks an order quantity and unit, requiring human review."
    },
    {
        "id": "E-039",
        "input": "50 mtr GI Pipe 25mm Class B",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Quantity '50 mtr' appears at the beginning of the line. Free-text grammar parses trailing quantities only, flagging MISSING_QUANTITY and routing to review."
    },
    {
        "id": "E-040",
        "input": "MS Hex Bolt M12x50 Grade 4.6 12.5 nos",
        "expected_outcome": "review",
        "expected_sku": None,
        "rationale": "Fractional quantity (12.5) for count unit 'nos' triggers blocking issue FRACTIONAL_COUNT. Bolts cannot be sold in half-units without review."
    }
]

def generate_pass2_submission():
    out_path = Path("/home/satjeet/Desktop/isocode/eval/second_pass/submissions/pass2_labels.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for c in SUBMISSION_CASES:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"Generated {len(SUBMISSION_CASES)} second-pass labels in {out_path}")

if __name__ == "__main__":
    generate_pass2_submission()
