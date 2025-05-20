# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import argparse
import base64
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from shutil import which
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s|%(levelname)s|%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def find_flatc_executable() -> str:
    flatc_path = which("flatc")
    if not flatc_path:
        raise FileNotFoundError("Unable to find the 'flatc' binary in PATH.")
    return flatc_path


def decode_inference_data(json_path: Path) -> Optional[bytes]:
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if "Inferences" not in data or not data["Inferences"]:
            logging.error("Missing or empty 'Inferences' array in JSON.")
            return None
        if "O" not in data["Inferences"][0]:
            logging.error("Missing 'O' key in the first inference entry.")
            return None

        return base64.b64decode(data["Inferences"][0]["O"])

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logging.error(f"Error parsing JSON structure: {e}")
    except OSError as e:
        logging.error(f"Error reading JSON file: {e}")
    return None


def run_flatc(schema_path: Path, binary_path: Path, output_dir: Path) -> None:
    """
    Run the 'flatc' tool on the given binary file using the specified schema.
    """
    flatc_cmd = [
        find_flatc_executable(),
        "--json",
        "--defaults-json",
        "--strict-json",
        "-o",
        str(output_dir),
        "--raw-binary",
        str(schema_path),
        "--",
        str(binary_path),
    ]

    logging.info(f"Executing command: {' '.join(flatc_cmd)}")
    try:
        subprocess.run(flatc_cmd, check=True, text=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"flatc command failed: {e}")
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Decode inference data from a JSON file and convert it to JSON using Flatbuffers."
    )
    parser.add_argument(
        "-i",
        "--input-file",
        type=Path,
        required=True,
        help="Path to the JSON file with base64-encoded inference data.",
    )
    parser.add_argument(
        "-f",
        "--fbs-path",
        type=Path,
        default=Path(
            "../../local-console/src/local_console/assets/schemas/objectdetection.fbs"
        ),
        help="Path to the FlatBuffers schema (.fbs) file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    logging.info("Decoding inference data from JSON...")
    inference_data = decode_inference_data(args.input_file)
    if inference_data is None:
        logging.error("Failed to decode inference data. Exiting.")
        return

    # Use a temporary directory for auxiliary files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        binary_path = tmpdir_path / "result.bin"
        json_output_path = tmpdir_path / "result.json"

        binary_path.write_bytes(inference_data)
        logging.info(f"Binary data written to: {binary_path}")

        # Convert binary to JSON using flatc
        run_flatc(args.fbs_path, binary_path, tmpdir_path)

        # Read and print the generated JSON output
        try:
            output_content = json_output_path.read_text(encoding="utf-8")
            logging.info("Flatc conversion successful. Generated JSON output:")
            print(output_content)
        except OSError as e:
            logging.error(f"Failed to read generated JSON file: {e}")


if __name__ == "__main__":
    main()
