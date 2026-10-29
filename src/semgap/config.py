"""Feature switches. FULL is the shipped engine; each flag can be turned off for ablation."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Config:
    negation: bool = True
    hedging: bool = True
    fuzzy: bool = True
    multilingual: bool = True
    inflection: bool = True       # plurals, hyphen/space compounds, slot frames
    text_quantities: bool = True  # numbers in text cross-checked; field named without a reading escalates
    cross_domain: bool = True
    ambiguity: bool = True
    require_clearance: bool = True


FULL = Config()
FLAGS = [f for f in Config.__dataclass_fields__]


def without(flag: str) -> Config:
    return replace(FULL, **{flag: False})
