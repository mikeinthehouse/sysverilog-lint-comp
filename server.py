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
origins = ["*"]  # Allow all origins for testing; update in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Regular expression to parse errors from Verible output
error_regex = re.compile(r'^(.*?):(\d+):(\d+): (warning|error): (.*)$')

def parse_linter_output(output: str):
    """Parse Verible output to extract errors and warnings."""
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

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
        tmp_file.write(code + "\n")
        filename = tmp_file.name

    try:
        logger.info(f"Running linter on file: {filename}")
        result = subprocess.run(
            [
                "verible-verilog-lint",
                "--rules=-module-filename",  # Disable specific linting rule
                "--lint_output_format=gnu",  # Use consistent output format
                filename,
            ],
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr
        errors = parse_linter_output(output)

        return {
            "errors": errors,
            "returncode": result.returncode,
            "raw_output": output,
        }
    except FileNotFoundError:
        logger.exception("Verible linter tool not found.")
        raise HTTPException(status_code=500, detail="Verible linter tool not found.")
    except Exception as e:
        logger.exception("An error occurred during linting.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")

@app.post("/compile")
async def compile_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
        tmp_file.write(code + "\n")
        filename = tmp_file.name

    try:
        logger.info(f"Running syntax checker on file: {filename}")
        result = subprocess.run(
            [
                "verible-verilog-syntax",
                "--lint_output_format=gnu",  # Ensure consistent output format
                filename,
            ],
            capture_output=True,
            text=True
        )

        output = result.stdout + result.stderr
        errors = parse_linter_output(output)

        return {
            "errors": errors,
            "returncode": result.returncode,
            "raw_output": output,
        }
    except FileNotFoundError:
        logger.exception("Verible syntax checker tool not found.")
        raise HTTPException(status_code=500, detail="Verible syntax checker tool not found.")
    except Exception as e:
        logger.exception("An error occurred during compilation.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
