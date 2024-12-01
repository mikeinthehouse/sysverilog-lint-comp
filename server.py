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
error_regex = re.compile(r'^(.*?):(\d+):(\d+)(?:-(\d+))?: (.*)$')

def parse_verible_output(output: str):
    """Parse Verible output to extract errors and warnings."""
    issues = []
    for line in output.splitlines():
        match = error_regex.match(line)
        if match:
            file_path, line_num, col_start, col_end, message = match.groups()
            # Infer severity based on message content
            if 'error' in message.lower() or 'syntax error' in message.lower():
                severity = 'error'
            elif 'warning' in message.lower():
                severity = 'warning'
            else:
                severity = 'info'  # Default to 'info' if severity is unclear
            issue = {
                "line": int(line_num),
                "column_start": int(col_start),
                "severity": severity,
                "message": message.strip()
            }
            if col_end:
                issue["column_end"] = int(col_end)
            issues.append(issue)
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
        all_issues = []

        # Syntax Checking
        logger.info(f"Running syntax check on file: {filename}")
            syntax_result = subprocess.run(
    [
        "verible-verilog-syntax",
        "--parse_fatal=false",  # Continue processing even if syntax errors are found
        filename
    ],
    capture_output=True,
    text=True
)

        syntax_output = syntax_result.stdout + syntax_result.stderr
        syntax_issues = parse_verible_output(syntax_output)
        all_issues.extend(syntax_issues)

        # Proceed to Linting even if there are syntax errors
        logger.info(f"Running linter on file: {filename}")
    lint_result = subprocess.run(
    [
        "verible-verilog-lint",
        "--rules=-module-filename",
        "--lint_fatal=false",  # Continue processing even if lint violations are found
        filename
    ],
    capture_output=True,
    text=True
)

        lint_output = lint_result.stdout + lint_result.stderr
        lint_issues = parse_verible_output(lint_output)
        all_issues.extend(lint_issues)

        return {
            "errors": all_issues,
            "returncode": max(syntax_result.returncode, lint_result.returncode),
            "raw_output": syntax_output + "\n" + lint_output,
            "file_content": code  # Include the original code in the response
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
