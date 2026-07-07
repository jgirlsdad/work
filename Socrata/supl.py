"""
Socrata Hope and Pray Upload Script

This script is a proof of concept that we can replace datasync with python. As such, it has been tested
to perform a replace on a test dataset. This reads in a csv file, and runs the 6 checks/cleaning steps below.
Note that the Date Validation has yet to be tested. This was successful in updating the dataset.
Testing now needs to be expanded to other data format, performing a append (replace transfer from a post to a put),
checking dates and boolean datatypes (Socrata Type Checkbox). I have set up a test dataset for testing ("rvak-43ap")

Column Check: Validates that the columns in the DataFrame match the expected columns from the type map,
    checking for missing, extra, and order-mismatched columns.
2. Numeric Cleaning: Cleans numeric columns by removing common formatting characters and converting them
    to numeric types, while tracking any errors and changes made.
3. Date Validation: Validates and optionally reformats date columns by attempting to parse them using a
    set of common date formats, while tracking any parsing errors.
4. Boolean Normalization: Cleans and normalizes boolean (checkbox) columns by converting common representations
    of true and false into consistent boolean values, while tracking any errors encountered during normalization.
5. String Length Check: Checks the lengths of string (text) columns and reports any values that exceed a
    specified maximum length (this stage is for reporting purposes only and does not modify the data).
6. JSON Serialization Check: Checks if the cleaned DataFrame can be successfully serialized to JSON format,
    which is important for downstream applications that require JSON data.
"""

import os
import sys
import argparse

import requests
import json
import pandas as pd
import time


# ---------------------------------------------------------------------------
# Check Functions
# ---------------------------------------------------------------------------

def getMetadata(w4x4, username, password, api):
    '''
    Fetches metadata for a given Socrata dataset.

    Parameters:
    - w4x4 (str): The dataset identifier.
    - username (str): The Socrata username.
    - password (str): The Socrata password.
    - api (str): The Socrata API token.

    Returns:
    - dict: A dictionary mapping column names to their data types.
    '''
    columns = {}
    meta = requests.get(
        f"https://data.colorado.gov/api/views/{w4x4}.json",
        headers={"X-App-Token": api},
        auth=(username, password),
    ).json()
   
    cols = meta["columns"]

    for c in cols:
        columns[c["fieldName"]] = c["dataTypeName"]

    return columns


def check_columns(df, type_map):
    '''
    Checks if the source data columns match the expected columns from the type map. The Socrata
    column names are case-insensitive, but the order must match exactly. Extra or missing columns will
    be reported as errors, while order mismatches will be reported as warnings.

    Parameters:
    - df (pd.DataFrame): The DataFrame to check.
    - type_map (dict): A dictionary mapping column names to their expected data types.

    Returns:
    - dict: A dictionary containing information about missing, extra, and order-mismatched columns,
      as well as a validity flag.
    '''
    df_cols = list(df.columns.str.lower())
    socrata_cols = list(type_map.keys())

    extra = set(df_cols) - set(socrata_cols)
    missing = set(socrata_cols) - set(df_cols)

    if not extra and not missing:
        order_mismatch = df_cols != socrata_cols
    else:
        order_mismatch = False

    return {
        "missing_columns": sorted(missing),
        "extra_columns": sorted(extra),
        "order_mismatch": order_mismatch,
        "valid": (
            len(missing) == 0 and
            len(extra) == 0 and
            not order_mismatch
        )
    }


def clean_numeric_columns(df, type_map):
    '''Cleans numeric columns in the DataFrame based on the provided type map. It identifies columns
    that are expected to be numeric, removes common formatting characters
    (commas, dollar signs, percent signs, parentheses), and attempts to convert them to
    numeric types. The function also tracks any errors encountered during conversion and any
    changes made to the original data.

    Parameters:
    - df (pd.DataFrame): The DataFrame to clean.
    - type_map (dict): A dictionary mapping column names to their expected data types. Only columns
      with types in the set {"number", "double", "money", "percent"} will be processed.

    Returns:
    - dict: A dictionary containing the cleaned DataFrame, any errors encountered, any changes made,
      and a validity flag.
    '''
    numeric_types = {"number", "double", "money", "percent"}

    df = df.copy()
    errors = {}
    changes = {}

    for col in df.columns:
        dtype = type_map.get(col.lower())
        if dtype not in numeric_types:
            continue

        original = df[col]

        # Clean string version
        cleaned = (
            original
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
            .str.strip()
        )

        # Convert to numeric
        converted = pd.to_numeric(cleaned, errors="coerce")

        # Missing logic
        is_missing = original.isna() | (cleaned == "")

        # Invalid values (fail)
        bad_mask = converted.isna() & (~is_missing)

        if bad_mask.any():
            errors[col] = {
                "bad_count": int(bad_mask.sum()),
                "examples": original.loc[bad_mask].head(5).tolist()
            }

        # --- CHANGE TRACKING ---
        original_str = original.astype(str)
        changed_mask = (original_str != cleaned) & (~is_missing)

        if changed_mask.any():
            changes[col] = {
                "count_changed": int(changed_mask.sum()),
                "examples_before": original.loc[changed_mask].head(3).tolist(),
                "examples_after": cleaned.loc[changed_mask].head(3).tolist()
            }
        else:
            changes[col] = {
                "count_changed": 0
            }

        # --- WRITE BACK ---
        df[col] = converted.astype(object)
        df.loc[converted.isna(), col] = ""

    return {
        "df": df,
        "errors": errors,
        "changes": changes,
        "valid": len(errors) == 0
    }


def validate_dates(
    df,
    type_map,
    date_formats=None,
    extra_date_formats=None,
    reformat=False
):
    '''Validates and optionally reformats date columns in the DataFrame based on the provided type map.
    It identifies columns that are expected to be dates, attempts to parse them using a set of common date
    formats (which can be extended with user-provided formats), and tracks any errors encountered during
    parsing. If reformatting is enabled and no parsing errors are found, it will reformat the dates into
    a consistent format (YYYY-MM-DD for date-only values and YYYY-MM-DD HH:MM:SS for datetime values).

    NOTE THIS HAS NOT BEEN TESTED AND HAS BEEN LEFT FOR THE NEXT PHASE.

    Parameters:
    - df (pd.DataFrame): The DataFrame to validate and reformat.
    - type_map (dict): A dictionary mapping column names to their expected data types. Only columns with
      the type "calendar_date" will be processed.
    - date_formats (dict, optional): A dictionary mapping column names to lists of date formats to try
      for parsing.
    - extra_date_formats (list, optional): A list of additional date formats to try for all date columns.
    - reformat (bool, optional): Whether to reformat successfully parsed dates into a consistent format.
    '''
    DEFAULT_DATE_FORMATS = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d-%b-%Y",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S %p %Z",
        "%Y-%m-%d %H:%M:%S",
    ]

    df = df.copy()
    errors = {}

    for col in df.columns:
        dtype = type_map.get(col)

        if dtype != "calendar_date":
            continue

        if date_formats and col in date_formats:
            formats = list(date_formats[col])
        else:
            formats = DEFAULT_DATE_FORMATS.copy()
            if extra_date_formats:
                formats.extend(extra_date_formats)

        original = df[col]
        stripped = original.astype(str).str.strip()

        matched = pd.Series(False, index=df.index)
        parsed_result = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")

        for fmt in formats:
            parsed = pd.to_datetime(original, format=fmt, errors="coerce")
            success = parsed.notna() & (~matched)

            matched = matched | parsed.notna()
            parsed_result.loc[success] = parsed.loc[success]

        is_missing = original.isna() | (stripped == "")
        bad_mask = (~matched) & (~is_missing)

        if bad_mask.any():
            errors[col] = {
                "bad_count": int(bad_mask.sum()),
                "examples": original.loc[bad_mask].head(5).tolist(),
                "formats_tried": formats
            }

        if reformat and not bad_mask.any():
            df[col] = parsed_result.astype(object)
            df.loc[parsed_result.isna(), col] = ""

            has_time = (
                (parsed_result.dt.hour != 0) |
                (parsed_result.dt.minute != 0) |
                (parsed_result.dt.second != 0)
            )

            date_only_mask = parsed_result.notna() & (~has_time)
            datetime_mask = parsed_result.notna() & has_time

            df.loc[date_only_mask, col] = (
                parsed_result.loc[date_only_mask]
                .dt.strftime("%Y-%m-%d")
            )

            df.loc[datetime_mask, col] = (
                parsed_result.loc[datetime_mask]
                .dt.strftime("%Y-%m-%d %H:%M:%S")
            )

    return {
        "df": df,
        "errors": errors,
        "valid": len(errors) == 0
    }


def check_json_serializable(df):
    '''Checks if the DataFrame can be serialized to JSON format.

    Parameters:
    - df (pd.DataFrame): The DataFrame to check for JSON serializability.

    Returns:
    - dict: A dictionary containing a validity flag and any error message encountered during
      JSON serialization.
    '''
    try:
        records = df.to_dict(orient="records")
        json.dumps(records)
        return {
            "valid": True,
            "error": None
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def clean_boolean_columns(df, type_map, normalize=True):
    '''Cleans and normalizes boolean (checkbox) columns in the DataFrame based on the provided type map.

    Parameters:
    - df (pd.DataFrame): The DataFrame to clean.
    - type_map (dict): A dictionary mapping column names to their expected data types. Only columns with
      the type "checkbox" will be processed.
    - normalize (bool, optional): Whether to normalize boolean values.

    Returns:
    - dict: A dictionary containing the cleaned DataFrame, any errors encountered, and a validity flag.
    '''
    df = df.copy()
    errors = {}

    true_values = {"y", "yes", "true", "1"}
    false_values = {"n", "no", "false", "0"}

    for col in df.columns:
        dtype = type_map.get(col)

        if dtype != "checkbox":
            continue

        if not normalize:
            continue

        original = df[col]
        cleaned = original.astype(str).str.strip().str.lower()

        # Masks
        is_missing = original.isna() | (cleaned == "")
        is_true = cleaned.isin(true_values)
        is_false = cleaned.isin(false_values)

        bad_mask = ~(is_true | is_false | is_missing)

        df.loc[is_true, col] = True
        df.loc[is_false, col] = False
        df.loc[is_missing, col] = ""

        if bad_mask.any():
            errors[col] = {
                "bad_count": int(bad_mask.sum()),
                "examples": original.loc[bad_mask].head(5).tolist()
            }

    return {
        "df": df,
        "errors": errors,
        "valid": len(errors) == 0
    }


def check_string_lengths(df, type_map, max_len=10000):
    '''Checks the lengths of string (text) columns in the DataFrame based on the provided type map.

    Parameters:
    - df (pd.DataFrame): The DataFrame to check.
    - type_map (dict): A dictionary mapping column names to their expected data types. Only columns with
      the type "text" will be processed.
    - max_len (int, optional): The maximum allowed length for string values. Default is 10,000.

    Returns:
    - dict: A dictionary containing a report of any string length issues found and a flag indicating
      whether any issues were found. The original DataFrame is not modified.
    '''
    issues = {}

    for col in df.columns:
        dtype = type_map.get(col)

        if dtype != "text":
            continue

        series = df[col].astype(str)
        lengths = series.str.len()

        long_mask = lengths > max_len

        if long_mask.any():
            issues[col] = {
                "count_exceeding": int(long_mask.sum()),
                "max_length_found": int(lengths.max()),
                "examples": series.loc[long_mask].head(3).tolist()
            }

    return {
        "issues": issues,
        "has_issues": len(issues) > 0
    }


def run_socrata_pipeline(
    df,
    type_map,
    date_formats=None,
    extra_date_formats=None,
    reformat_dates=True,
    normalize_booleans=True,
    max_string_length=10000
):
    '''Runs the full data validation and cleaning pipeline on a DataFrame.

    Parameters:
    - df (pd.DataFrame): The DataFrame to process through the pipeline.
    - type_map (dict): A dictionary mapping column names to their expected data types.
    - date_formats (dict, optional): Column-specific date format overrides.
    - extra_date_formats (list, optional): Additional date formats to try for all date columns.
    - reformat_dates (bool, optional): Whether to reformat parsed dates to a consistent format.
    - normalize_booleans (bool, optional): Whether to normalize boolean (checkbox) columns.
    - max_string_length (int, optional): Maximum allowed string length for text columns.

    Returns:
    - dict: A dictionary with keys "valid", "stage", "results", and "df".
    '''
    results = {}

    # --- 1. Column Check ---
    col_check = check_columns(df, type_map)
    results["columns"] = col_check

    if not col_check["valid"]:
        return {
            "valid": False,
            "stage": "columns",
            "results": results,
            "df": None
        }

    # --- 2. Numeric Cleaning ---
    num_result = clean_numeric_columns(df, type_map)
    results["numeric"] = num_result

    if not num_result["valid"]:
        return {
            "valid": False,
            "stage": "numeric",
            "results": results,
            "df": None
        }

    df_work = num_result["df"]

    # --- 3. Date Validation ---
    date_result = validate_dates(
        df_work,
        type_map,
        date_formats=date_formats,
        extra_date_formats=extra_date_formats,
        reformat=reformat_dates
    )
    results["dates"] = date_result

    if not date_result["valid"]:
        return {
            "valid": False,
            "stage": "dates",
            "results": results,
            "df": None
        }

    df_work = date_result["df"]

    # --- 4. Boolean Normalization ---
    bool_result = clean_boolean_columns(
        df_work,
        type_map,
        normalize=normalize_booleans
    )
    results["boolean"] = bool_result

    if not bool_result["valid"]:
        return {
            "valid": False,
            "stage": "boolean",
            "results": results,
            "df": None
        }

    df_work = bool_result["df"]

    # --- 5. String Length Check (REPORT ONLY) ---
    length_result = check_string_lengths(
        df_work,
        type_map,
        max_len=max_string_length
    )
    results["string_length"] = length_result

    # --- 6. JSON Serialization Check ---
    json_result = check_json_serializable(df_work)
    results["json"] = json_result

    if not json_result["valid"]:
        return {
            "valid": False,
            "stage": "json",
            "results": results,
            "df": None
        }

    # --- SUCCESS ---
    return {
        "valid": True,
        "stage": "complete",
        "results": results,
        "df": df_work
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the Socrata upload validation pipeline and replace operation."
    )
    parser.add_argument(
        "-w",
        "--dataset-id",
        help="Socrata dataset identifier (4x4).",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="Path to input CSV.",
    )
    args = parser.parse_args(argv)

    w4x4 = args.dataset_id
    file = args.file
    bic_home = os.getenv("bic_etl_home")
    config_path = f"{bic_home}/general/datasync/config.json"
    #file_path = f"{bic_home}/{file}"
    file_path = file

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        return 1
    if not os.path.exists(file_path):
        print(f"ERROR: Input file not found: {file_path}")
        return 1
    
    with open(config_path) as flog:
        info = json.load(flog)

    username = info['username']
    password = info['password']
    api = info['appToken']

    columns = getMetadata(w4x4, username, password, api)
    df = pd.read_csv(file_path)

    res = run_socrata_pipeline(df, columns)

    if not res["valid"]:
        print(f"Validation failed at stage: {res['stage']}")
        print(json.dumps(res["results"], indent=2, default=str))
        return 1

    max_retries = 5
    base_url = "https://data.colorado.gov"
    retry_delay = 5

    df = res["df"]
    df = df.fillna("")
    data = df.to_dict(orient="records")

    url = f"{base_url}/resource/{w4x4}.json"

    for attempt in range(max_retries):
        response = requests.put(
            url,
            headers={"X-App-Token": api},
            auth=(username, password),
            json=data
        )

        if response.status_code == 200:
            print(f"Replace successful ({len(data)} rows)")
            return 0

        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    print(
        "Replace failed after "
        f"{max_retries} attempts. Last status: {response.status_code}"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
