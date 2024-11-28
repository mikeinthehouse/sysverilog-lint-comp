from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import logging
import os
import tempfile
import re

app = FastAPI()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Pydantic Model
class LintRequest(BaseModel):
    code: str

# CORS configuration
origins = [
    "https://your-netlify-app.netlify.app",  # Replace with your actual frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins during testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regular expression to parse error messages
error_regex = re.compile(r'^(.*?):(\d+):(\d+): (warning|error): (.*)$')

def parse_linter_output(output):
    errors = []
    for line in output.splitlines():
        match = error_regex.match(line)
        if match:
            file_path, line_num, col_num, severity, message = match.groups()
            errors.append({
                "line": int(line_num),
                "column": int(col_num),
                "severity": severity,
                "message": message.strip()
            })
    return errors

@app.post("/lint")
async def lint_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    # Create a temporary file with the provided code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
        tmp_file.write(code + "\n")  # Ensure the file ends with a newline
        filename = tmp_file.name

    try:
        logger.info(f"Linting file: {filename}")

        # Run Verible lint with updated flags
        result = subprocess.run(
            [
                "verible-verilog-lint",
                "--rules=-module-filename",
                "--parse_fatal=false",
                "--lint_fatal=false",
                "--limit=0",
                "--lint_output_format=gnu",
                filename
            ],
            capture_output=True,
            text=True
        )

        logger.info(f"Linting completed with return code {result.returncode}.")

        # Combine stdout and stderr
        output = result.stdout + result.stderr

        # Parse the linting output
        lint_errors = parse_linter_output(output)

        # Include raw output for debugging
        return {
            "errors": lint_errors,
            "returncode": result.returncode,
            "raw_output": output  # Include raw linter output
        }

    except FileNotFoundError:
        logger.exception("Verible linter not found.")
        raise HTTPException(status_code=500, detail="Verible linter not found.")
    except Exception as e:
        logger.exception("An error occurred during linting.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")

@app.post("/compile")
async def compile_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    # Create a temporary file with the provided code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
        tmp_file.write(code + "\n")
        filename = tmp_file.name

    try:
        logger.info(f"Compiling file: {filename}")

        # Run Verible's syntax checker with updated flags
        result = subprocess.run(
            [
                "verible-verilog-syntax",
                "--parse_fatal=false",
                "--limit=0",
                "--lint_output_format=gnu",
                filename
            ],
            capture_output=True,
            text=True
        )

        logger.info(f"Compilation completed with return code {result.returncode}.")

        # Combine stdout and stderr
        output = result.stdout + result.stderr

        # Parse the syntax checker output
        compile_errors = parse_linter_output(output)

        # Include raw output for debugging
        return {
            "errors": compile_errors,
            "returncode": result.returncode,
            "raw_output": output
        }

    except FileNotFoundError:
        logger.exception("Verible syntax checker not found.")
        raise HTTPException(status_code=500, detail="Verible syntax checker not found.")
    except Exception as e:
        logger.exception("An error occurred during compilation.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
