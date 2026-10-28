"""Builds docs/HealthNexus_RAG_Guide.pdf.

    cd backend && python ../docs/rag_guide/build.py

Run from `backend/` (the catalog is imported live, so the 29-query tables always match the code). The timings come
from docs/rag_guide/measurements.json; refresh them with `python ../docs/rag_guide/measure.py` (database running).
Needs Chrome or Edge, and PyMuPDF.
"""

import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "citizen_guide"))
sys.path.insert(0, str(HERE))
warnings.filterwarnings("ignore")

import builder  # noqa: E402
import rag_a, rag_b, rag_c  # noqa: E402
from lib import ROOT  # noqa: E402

if __name__ == "__main__":
    builder.run(
        parts=[rag_a, rag_b, rag_c],
        out=ROOT / "docs" / "HealthNexus_RAG_Guide.pdf",
        work=HERE,
        title_html="HealthNexus<br>Nira and the RAG pipeline",
        subtitle="How it answers only related questions, the 29 queries, the pipeline, how to defend the name, the files, the stack and the speed",
        meta="For reading and for defence: every query table is generated from the live catalog; every timing was measured on this machine.",
        footer="HealthNexus · RAG guide",
        doc_title="HealthNexus: RAG guide",
    )
