from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.benchmark.document_conversion import BENCHMARK_BACKENDS, run_document_conversion_benchmark


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the offline document-conversion benchmark for the annual-report pilot set.",
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        default=list(BENCHMARK_BACKENDS),
        help=f"Backends to evaluate. Defaults to: {', '.join(BENCHMARK_BACKENDS)}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. Defaults to stdout-only.",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    result = await run_document_conversion_benchmark(None, backends=tuple(args.backends))

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Wrote benchmark JSON to {args.output}")

    print(f"Recommended default backend: {result['recommended_default_backend']}")
    print("Backend summary:")
    for backend, summary in result["backend_summary"].items():
        print(f"- {backend}: {json.dumps(summary, ensure_ascii=False, default=str)}")

    print("Per-report results:")
    for report in result["reports"]:
        print(f"- {report['report_key']}:")
        for row in report["results"]:
            print(
                "  "
                f"{row['backend']} | "
                f"score={row['score']} | "
                f"project_recall={row['project_recall']} | "
                f"family_recall={row['family_recall']} | "
                f"field_coverage={row['field_coverage']} | "
                f"unmatched_rate={row['unmatched_rate']} | "
                f"table_quality={row['table_quality']} | "
                f"provenance={row['provenance_preservation']}"
            )
            if row.get("error"):
                print(f"    error={row['error']}")


if __name__ == "__main__":
    asyncio.run(_main())
