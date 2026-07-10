from __future__ import annotations

from pathlib import Path

from audit_risk_mapper.model_training import load_pair_features

if __name__ == "__main__":
    x, y = load_pair_features(Path(__file__).resolve().parents[1])
    print({"rows": len(x), "labels": sorted(set(y))})
