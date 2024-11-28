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

    # Extract module name using regex
    match = re.search(r'\bmodule\s+(\w+)', code)
    if not match:
        logger.error("No module declaration found.")
        raise HTTPException(status_code=400, detail="No module declaration found.")

    # Initialize filenames
    code_filename = None
    config_filename = None

    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_code_file:
            tmp_code_file.write(code + "\n")  # Ensure the file ends with a newline
            code_filename = tmp_code_file.name

        # Create a temporary configuration file to disable the 'module-filename' rule
        with tempfile.NamedTemporaryFile(mode="w", suffix=".rules.verible_lint", delete=False) as tmp_config_file:
            tmp_config_file.write("disable_rules: module-filename\n")
            config_filename = tmp_config_file.name

        logger.info(f"Linting file: {code_filename} with config: {config_filename}")

        # Run Verible lint with the configuration file
        result = subprocess.run(
            ["verible-verilog-lint", f"--rules_config={config_filename}", code_filename],
            capture_output=True,
            text=True
        )

        logger.info(f"Linting completed with return code {result.returncode}.")

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        logger.exception("Verible linter not found.")
        raise HTTPException(status_code=500, detail="Verible linter not found.")
    except Exception as e:
        logger.exception("An error occurred during linting.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary files
        for filename in [code_filename, config_filename]:
            if filename and os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Temporary file {filename} removed.")

@app.post("/compile")
async def compile_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    # Extract module name using regex
    match = re.search(r'\bmodule\s+(\w+)', code)
    if not match:
        logger.error("No module declaration found.")
        raise HTTPException(status_code=400, detail="No module declaration found.")

    # Initialize filename
    code_filename = None

    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_code_file:
            tmp_code_file.write(code + "\n")  # Ensure the file ends with a newline
            code_filename = tmp_code_file.name

        logger.info(f"Compiling file: {code_filename}")

        # Run Verible's syntax checker (verible-verilog-syntax)
        result = subprocess.run(
            ["verible-verilog-syntax", code_filename],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("Syntax check passed.")
            return {
                "stdout": "Syntax check passed.",
                "stderr": "",
                "returncode": 0
            }
        else:
            logger.error("Syntax errors found.")
            return {
                "stdout": "",
                "stderr": result.stderr,
                "returncode": 1
            }
    except FileNotFoundError:
        logger.exception("Verible syntax checker not found.")
        raise HTTPException(status_code=500, detail="Verible syntax checker not found.")
    except Exception as e:
        logger.exception("An error occurred during syntax checking.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if code_filename and os.path.exists(code_filename):
            os.remove(code_filename)
            logger.info(f"Temporary file
