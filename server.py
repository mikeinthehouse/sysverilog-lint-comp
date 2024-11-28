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

# Regular expression to parse errors from Verible's default output
error_regex = re.compile(r'^(.*?):(\d+):(\d+): (.*)$')

def parse_verible_output(output: str):
    """Parse Verible output to extract errors and warnings."""
    issues = []
    for line in output.splitlines():
        match = error_regex.match(line)
        if match:
            file_path, line_num, col_num, message = match.groups()
            # Determine severity based on keywords in the message
            severity = 'error' if 'error' in message.lower() else 'warning'
            issues.append({
                "line": int(line_num),
                "column": int(col_num),
                "severity": severity,
                "message": message.strip()
            })
    return issues

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
        # First Pass: Syntax Checking
        logger.info(f"Running syntax check on file: {filename}")
        syntax_result = subprocess.run(
            ["verible-verilog-syntax", filename],
            capture_output=True,
            text=True
        )

        syntax_output = syntax_result.stdout + syntax_result.stderr
        syntax_issues = parse_verible_output(syntax_output)

        if syntax_result.returncode != 0:
            # If there are syntax errors, return them without proceeding to linting
            return {
                "errors": syntax_issues,
                "returncode": syntax_result.returncode,
                "raw_output": syntax_output,
            }

        # Second Pass: Linting
        logger.info(f"Running linter on file: {filename}")
        lint_result = subprocess.run(
            ["verible-verilog-lint", "--rules=-module-filename", filename],
            capture_output=True,
            text=True
        )

        lint_output = lint_result.stdout + lint_result.stderr
        lint_issues = parse_verible_output(lint_output)

        # Combine syntax and lint issues
        all_issues = syntax_issues + lint_issues

        return {
            "errors": all_issues,
            "returncode": lint_result.returncode,
            "raw_output": syntax_output + "\n" + lint_output,
        }
    except FileNotFoundError as e:
        logger.exception("Verible tool not found.")
        raise HTTPException(status_code=500, detail=f"Verible tool not found: {e}")
    except Exception as e:
        logger.exception("An error occurred during linting.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
