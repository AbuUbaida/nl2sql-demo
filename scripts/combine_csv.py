import argparse
import sys
from pathlib import Path

import pandas as pd

# Known misspellings/variants in source files, mapped to their correct name.
COLUMN_ALIASES = {
    "categtory": "category",
}


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names by stripping whitespace, lowercasing, replacing
    spaces/hyphens with underscores, and fixing known misspellings so that
    files from different sources line up under the same column names.
    """
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_").str.replace("-", "_")
    df = df.rename(columns=COLUMN_ALIASES)
    return df


def combine_csvs(input_dir: Path, output_path: Path) -> None:
    output_path = output_path.resolve()
    csv_paths = sorted(p for p in input_dir.glob("*.csv") if p.resolve() != output_path)
    if not csv_paths:
        raise ValueError(f"No CSV files found in {input_dir}")

    frames = []
    reference_columns = None
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        df = normalize_column_names(df)

        if reference_columns is None:
            reference_columns = df.columns.tolist()
        elif set(df.columns) != set(reference_columns):
            raise ValueError(
                f"{csv_path.name} has columns {df.columns.tolist()}, "
                f"expected {reference_columns}"
            )

        frames.append(df[reference_columns])

    combined = pd.concat(frames, ignore_index=True)
    combined.columns = combined.columns.str.replace("_", " ").str.upper()
    combined.to_csv(output_path, index=False)
    print(f"Combined {len(csv_paths)} files into {output_path} ({len(combined)} rows).")


def main():
    parser = argparse.ArgumentParser(description="Combine all CSV files in a directory into one CSV.")
    parser.add_argument("--input-dir", type=Path, default=Path("data"), help="Directory containing CSV files (default: data)")
    parser.add_argument("--output", type=Path, default=Path("data/combined.csv"), help="Output CSV path (default: data/combined.csv)")
    args = parser.parse_args()

    try:
        combine_csvs(args.input_dir, args.output)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
