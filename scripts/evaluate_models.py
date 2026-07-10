from __future__ import annotations

from pathlib import Path

from audit_risk_mapper.evaluation import summarize_generated_data

if __name__ == "__main__":
    print(summarize_generated_data(Path(__file__).resolve().parents[1]))
