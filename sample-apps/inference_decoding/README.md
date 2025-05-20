# Convert inferences into human-readable

This Python script processes an inference extracted from Local Console, and converts it into a human-readable JSON format using`flatc` tool from flatbuffers.

## Prerequisites

* [flatc](https://github.com/google/flatbuffers/releases/tag/v24.3.25)

Ensure these programs are added to your system's `PATH` environment variable.

## Usage

## Input File

You can obtain inference files from the Inference HUB through the Local Console UI. These files are located in the "Inference Folder Path".

The input JSON must contain an `Inferences` array with base64-encoded inference data in the following format:

```json
{
    "Inferences": [
        {
            "O": "base64_encoded_inference_data"
        }
    ]
}
```

## Run

To decode and process the inferences, use the following command:

```sh
python decode.py \
  --input-file ./20241216114945300.txt
```

The decoded, human-readable JSON will be output to your console.
