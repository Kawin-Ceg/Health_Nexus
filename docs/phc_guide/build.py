"""Builds docs/HealthNexus_PHC_Worker_Guide.pdf.

    python docs/phc_guide/build.py

Shares the builder and helpers with the citizen guide (docs/citizen_guide). Every file:line is looked up in the
live code, so a renamed or moved function stops the build instead of printing a wrong line number.
Needs Chrome or Edge, and PyMuPDF (pip install pymupdf).
"""

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "citizen_guide"))
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

import builder  # noqa: E402
import phc_a, phc_b, phc_c, phc_d  # noqa: E402
from lib import ROOT  # noqa: E402

if __name__ == "__main__":
    builder.run(
        parts=[phc_a, phc_b, phc_c, phc_d],
        out=ROOT / "docs" / "HealthNexus_PHC_Worker_Guide.pdf",
        work=HERE,
        title_html="HealthNexus<br>PHC worker module",
        subtitle="Full-stack guide: every feature, its files, its key functions and how they talk to each other",
        meta=(
            "Features covered: joining and approval, dashboard, alerts worklist, citizens, citizen record, examinations, "
            "schedule and visits, reports and risk map, outbreak signals, advisories, complaints, Nira, profile, settings"
        ),
        footer="HealthNexus · PHC worker guide",
        doc_title="HealthNexus: PHC worker module guide",
    )
