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
    "https://your-netlify-app.netlify.app",  # Replace with your actual Netlify app URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins or specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        # Run Verible lint with adjusted flags
        result = subprocess.run(
            [
                "verible-verilog-lint",
                "--rules=-module-filename",
                "--lint_fatal_errors=false",
                "--parse_fatal=false",
                "--error_limit=0",
                filename
            ],
            capture_output=True,
            text=True
        )

        logger.info(f"Linting completed with return code {result.returncode}.")

        # Combine stdout and stderr
        output = result.stdout + result.stderr

        # Parse the linting output to extract line numbers and messages
        lint_errors = []
        for line in output.splitlines():
            # Adjusted regular expression to capture different error formats
            match = re.match(r'^(.*?):(\d+):(\d+)(?:-(\d+))?: (.*)$', line)
            if match:
                file_path, line_num, col_start, col_end, message = match.groups()
                error_entry = {
                    "line": int(line_num),
                    "column_start": int(col_start),
                    "message": message.strip()
                }
                if col_end:
                    error_entry["column_end"] = int(col_end)
                lint_errors.append(error_entry)

        return {
            "errors": lint_errors,
            "returncode": result.returncode
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
        tmp_file.write(code + "\n")  # Ensure the file ends with a newline
        filename = tmp_file.name

    try:
        logger.info(f"Compiling file: {filename}")

        # Run Verible's syntax checker with adjusted flags
        result = subprocess.run(
            [
                "verible-verilog-syntax",
                "--parse_fatal=false",
                "--error_limit=0",
                filename
            ],
            capture_output=True,
            text=True
        )

        logger.info(f"Compilation completed with return code {result.returncode}.")

        # Combine stdout and stderr
        output = result.stdout + result.stderr

        # Parse the syntax checker output to extract line numbers and messages
        compile_errors = []
        for line in output.splitlines():
            # Adjusted regular expression
            match = re.match(r'^(.*?):(\d+):(\d+)(?:-(\d+))?: (.*)$', line)
            if match:
                file_path, line_num, col_start, col_end, message = match.groups()
                error_entry = {
                    "line": int(line_num),
                    "column_start": int(col_start),
                    "message": message.strip()
                }
                if col_end:
                    error_entry["column_end"] = int(col_end)
                compile_errors.append(error_entry)

        return {
            "errors": compile_errors,
            "returncode": result.returncode
        }

    except FileNotFoundError:
        logger.exception("Verible syntax checker not found.")
        raise HTTPException(status_code=500, detail="Verible syntax checker not found.")
    except Exception as e:
        logger.exception("An error occurred during compilation.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
