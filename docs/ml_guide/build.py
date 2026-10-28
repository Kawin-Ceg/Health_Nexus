"""Builds docs/HealthNexus_ML_Guide.pdf.

    cd backend && python ../docs/ml_guide/build.py

Run from `backend/` (the scorer and the model loader read `.env`). The worked examples and the parameter tables are
computed from the live scorer, the reports in model/reports and docs/ml_guide/measurements.json (refresh the
timings with `python ../docs/ml_guide/measure.py`). Needs Chrome or Edge, and PyMuPDF.
"""

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "citizen_guide"))
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

import builder  # noqa: E402
import ml_a, ml_b, ml_c, ml_d  # noqa: E402
from lib import ROOT  # noqa: E402

if __name__ == "__main__":
    builder.run(
        parts=[ml_a, ml_b, ml_c, ml_d],
        out=ROOT / "docs" / "HealthNexus_ML_Guide.pdf",
        work=HERE,
        title_html="HealthNexus<br>The ML explained",
        subtitle="Features, the personal baseline, hyperparameters, how severity is decided, false-positive reduction, the pipeline and where the model lives",
        meta="For reading and for defence: every number is from the code, the reports in model/reports, or a measurement made on this machine.",
        footer="HealthNexus · ML guide",
        doc_title="HealthNexus: ML guide",
    )
