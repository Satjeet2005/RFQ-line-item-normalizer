"""
Proposed deterministic matching engine.
Conforms to PRD Section E Workflows 4 & 5 and PRD_DECISIONS.md D1, D3, D11, D13.
"""
from typing import Dict, List, Optional, Set, Tuple, Any
from domain.types import NormalizedLine, Candidate, MatchResult
from domain.units import check_unit_compatibility
from domain.normalizer import (
    clean_text_nfkc,
    build_normalized_description_and_tokens,
    normalize_line
)

def dice_similarity(r_tokens: Set[str], c_tokens: Set[str]) -> float:
    """Calculate Dice similarity coefficient: 2 * |R ∩ C| / (|R| + |C|)."""
    if not r_tokens or not c_tokens:
        return 0.0
    intersection = len(r_tokens & c_tokens)
    return (2.0 * intersection) / (len(r_tokens) + len(c_tokens))

class ProposedMatcher:
    def __init__(self, catalog: List[Dict[str, Any]], config: Dict[str, Any]):
        self.catalog = sorted(catalog, key=lambda x: x["sku"])
        self.k: int = int(config.get("K", 5))
        self.t_min_candidate: float = float(config.get("T_MIN_CANDIDATE", 0.30))
        self.t_propose: float = float(config.get("T_PROPOSE", 0.60))
        self.t_margin: float = float(config.get("T_MARGIN", 0.10))

        # Pre-tokenize catalog products
        self.catalog_items = []
        for item in self.catalog:
            sku = item["sku"]
            name = item["name"]
            category = item.get("category", "")
            uom = item.get("uom", "")
            attributes = item.get("attributes", {})
            aliases = item.get("aliases", [])

            # Spec tokens from attributes
            spec_tokens = set()
            if "material" in attributes:
                spec_tokens.add(f"material:{attributes['material']}")
            if "class" in attributes:
                spec_tokens.add(f"class:{attributes['class']}")
            if "grade" in attributes:
                spec_tokens.add(f"grade:{attributes['grade']}")
            if "thread" in attributes:
                spec_tokens.add(f"thread:{attributes['thread']}")
            if "length_mm" in attributes:
                spec_tokens.add(f"length:{attributes['length_mm']}")
            if "size_mm" in attributes:
                spec_tokens.add(f"size:{attributes['size_mm']}")

            # Name tokens: normalize using normalize_line for symmetric token derivation
            norm_name = normalize_line(name)
            name_token_set = set(norm_name.tokens) | spec_tokens

            # Alias token sets
            alias_token_sets = []
            for alias in aliases:
                norm_alias = normalize_line(alias)
                alias_token_sets.append(set(norm_alias.tokens) | spec_tokens)

            self.catalog_items.append({
                "sku": sku,
                "name": name,
                "category": category,
                "uom": uom,
                "attributes": attributes,
                "name_tokens": name_token_set,
                "alias_token_sets": alias_token_sets
            })

    def match(self, line: NormalizedLine) -> MatchResult:
        r_tokens = set(line.tokens)
        if not r_tokens:
            return MatchResult(
                system_outcome="unmatched",
                candidates=[],
                reason_codes=["NO_CANDIDATE"]
            )

        # 1. Score all catalog products
        scored = []
        for item in self.catalog_items:
            sim_name = dice_similarity(r_tokens, item["name_tokens"])
            sim_aliases = [dice_similarity(r_tokens, a_tok) for a_tok in item["alias_token_sets"]]
            best_sim = max([sim_name] + sim_aliases) if sim_aliases else sim_name
            sim_rounded = round(best_sim, 4)

            if sim_rounded >= self.t_min_candidate:
                scored.append((sim_rounded, item))

        if not scored:
            return MatchResult(
                system_outcome="unmatched",
                candidates=[],
                reason_codes=["NO_CANDIDATE"]
            )

        # 2. Total ordering: descending similarity, ascending SKU
        scored.sort(key=lambda x: (-x[0], x[1]["sku"]))
        top_scored = scored[:self.k]

        # 3. Per-candidate checks: spec conflict and unit check
        candidates: List[Candidate] = []
        for score, item in top_scored:
            sku = item["sku"]
            name = item["name"]
            uom = item["uom"]
            attributes = item["attributes"]
            flags: List[str] = []
            disqualified = False

            # Spec conflict check
            for req_attr, req_val in line.spec.items():
                cand_val = attributes.get(req_attr)
                if cand_val is None or cand_val != req_val:
                    flags.append(f"SPEC_CONFLICT:{req_attr}")
                    disqualified = True

            # Unit check
            _, unit_flag = check_unit_compatibility(line.unit, uom)
            if unit_flag:
                flags.append(unit_flag)

            candidates.append(Candidate(
                sku=sku,
                name=name,
                similarity=score,
                disqualified=disqualified,
                flags=flags,
                uom=uom,
                attributes=attributes
            ))

        # 4. Plausible set P
        p_candidates = [c for c in candidates if not c.disqualified]
        if not p_candidates:
            return MatchResult(
                system_outcome="unmatched",
                candidates=candidates,
                reason_codes=["NO_COMPATIBLE_CANDIDATE"]
            )

        # 5. Near-tie group G = candidates in P with s1 - s_c < T_MARGIN
        top_p = p_candidates[0]
        s1 = top_p.similarity
        g_candidates = [c for c in p_candidates if (s1 - c.similarity) < self.t_margin]

        # 6. Decision procedure: collect abstention reasons
        reasons: List[str] = []

        # Near-tie / missing discriminator
        if len(g_candidates) >= 2:
            # Check if members differ on an attribute the request does not specify
            g_all_attrs = set()
            for c in g_candidates:
                g_all_attrs.update(c.attributes.keys())
            unspecified_attrs = [a for a in g_all_attrs if a not in line.spec]
            differ_on_unspecified = False
            for a in unspecified_attrs:
                vals = set(c.attributes.get(a) for c in g_candidates if a in c.attributes)
                if len(vals) > 1:
                    differ_on_unspecified = True
                    break

            if differ_on_unspecified:
                reasons.append("SPEC_MISSING_DISCRIMINATOR")
            else:
                reasons.append("MULTIPLE_CANDIDATES")

        # Low similarity
        if s1 < self.t_propose:
            reasons.append("LOW_SIMILARITY")

        # Blocking request issues
        for code in line.issue_codes:
            if code in (
                "MISSING_QUANTITY",
                "MISSING_UNIT",
                "UNKNOWN_UNIT",
                "UNIT_CONFLICT",
                "FRACTIONAL_COUNT",
                "SPEC_CONFLICT_IN_REQUEST"
            ):
                if code not in reasons:
                    reasons.append(code)

        # Unit incompatibility with top candidate in P
        if "UNIT_INCOMPATIBLE" in top_p.flags:
            if "UNIT_INCOMPATIBLE" not in reasons:
                reasons.append("UNIT_INCOMPATIBLE")

        # Close textual match with spec conflict cannot override to propose a lower candidate
        if candidates[0].disqualified:
            if "SPEC_CONFLICT" not in reasons:
                reasons.append("SPEC_CONFLICT")

        if reasons:
            return MatchResult(
                system_outcome="ambiguous",
                candidates=candidates,
                reason_codes=reasons
            )

        # No abstention reasons: propose top candidate
        return MatchResult(
            system_outcome="proposed",
            candidates=candidates,
            reason_codes=[]
        )
