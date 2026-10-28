"""Builds docs/HealthNexus_Citizen_Module_Guide.pdf.

    python docs/citizen_guide/build.py

Every file:line in the guide is looked up in the live code (lib.find), so renaming a function
or moving it makes this script stop with the reference that no longer exists.
Needs Chrome or Edge, and PyMuPDF (pip install pymupdf).
"""

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

import builder  # noqa: E402
import part_a, part_b, part_c, part_d  # noqa: E402
from lib import ROOT  # noqa: E402

if __name__ == "__main__":
    builder.run(
        parts=[part_a, part_b, part_c, part_d],
        out=ROOT / "docs" / "HealthNexus_Citizen_Module_Guide.pdf",
        work=HERE,
        title_html="HealthNexus<br>Citizen module",
        subtitle="Full-stack guide: every feature, its files, its key functions and how they talk to each other",
        meta=(
            "Features covered: account, onboarding, smartwatch, scoring pipeline, dashboard, history, alerts and advisories, "
            "visits, Nira assistant, profile, settings"
        ),
        footer="HealthNexus · Citizen module guide",
        doc_title="HealthNexus: Citizen module guide",
    )
