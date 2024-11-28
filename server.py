from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import re
import logging
import os
import tempfile

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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["POST"],
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

        # Run Verible lint
        result = subprocess.run(
            ["verible-verilog-lint", "--rules=-module-filename", filename],
            capture_output=True,
            text=True
        )

        logger.info(f"Linting completed with return code {result.returncode}.")

        # Parse the linting output to extract line numbers and messages
        lint_errors = []
        for line in result.stdout.splitlines():
            match = re.match(r'^(.*?):(\d+):(\d+): (.*)$', line)
            if match:
                file_path, line_num, col_num, message = match.groups()
                lint_errors.append({
                    "line": int(line_num),
                    "column": int(col_num),
                    "message": message.strip()
                })

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

        # Run Verible's linter as a syntax checker
        result = subprocess.run(
            ["verible-verilog-lint", "--parse_fatal", filename],
            capture_output=True,
            text=True
        )

        logger.info(f"Compilation completed with return code {result.returncode}.")

        # Parse the linter output to extract line numbers and messages
        compile_errors = []
        for line in result.stdout.splitlines():
            match = re.match(r'^(.*?):(\d+):(\d+): (.*)$', line)
            if match:
                file_path, line_num, col_num, message = match.groups()
                compile_errors.append({
                    "line": int(line_num),
                    "column": int(col_num),
                    "message": message.strip()
                })

        return {
            "errors": compile_errors,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        logger.exception("Verible linter not found.")
        raise HTTPException(status_code=500, detail="Verible linter not found.")
    except Exception as e:
        logger.exception("An error occurred during compilation.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
