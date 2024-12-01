from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import logging
import os
import tempfile
import re
import copy

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
    code = payload.code.rstrip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    # Split the code into lines
    code_lines = code.split('\n')
    all_issues = []
    modified_code_lines = copy.deepcopy(code_lines)
    iterations = 0
    max_iterations = 100  # Prevent infinite loops

    while iterations < max_iterations:
        # Create a temporary file with the modified code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
            tmp_file.write('\n'.join(modified_code_lines) + "\n")
            filename = tmp_file.name

        try:
            logger.info(f"Running syntax check on file: {filename}")
            result = subprocess.run(
                [
                    "verible-verilog-syntax",
                    filename
                ],
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr
            issues = parse_verible_output(output)

            if not issues:
                # No more errors
                break
            else:
                # Store the first error
                first_issue = issues[0]
                line_number = first_issue['line']
                all_issues.append(first_issue)

                # Comment out the line with the error
                if 0 <= line_number - 1 < len(modified_code_lines):
                    # Preserve indentation
                    line_content = modified_code_lines[line_number - 1]
                    if not line_content.strip().startswith('//'):
                        modified_code_lines[line_number - 1] = '// ' + line_content
                else:
                    # Line number out of range
                    break
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

        iterations += 1

    return {
        "errors": all_issues,
        "returncode": 1 if all_issues else 0,
        "file_content": code  # Include the original code in the response
    }

@app.post("/compile")
async def compile_code(payload: LintRequest):
    code = payload.code.rstrip()
    if not code:
        logger.error("No code provided.")
        raise HTTPException(status_code=400, detail="No code provided.")

    # Split the code into lines
    code_lines = code.split('\n')
    all_issues = []
    modified_code_lines = copy.deepcopy(code_lines)
    iterations = 0
    max_iterations = 100  # Prevent infinite loops

    while iterations < max_iterations:
        # Create a temporary file with the modified code
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as tmp_file:
            tmp_file.write('\n'.join(modified_code_lines) + "\n")
            filename = tmp_file.name

        try:
            logger.info(f"Running syntax check on file: {filename}")
            result = subprocess.run(
                [
                    "verible-verilog-syntax",
                    filename
                ],
                capture_output=True,
                text=True
            )

            output = result.stdout + result.stderr
            issues = parse_verible_output(output)

            if not issues:
                # No more errors
                break
            else:
                # Store the first error
                first_issue = issues[0]
                line_number = first_issue['line']
                all_issues.append(first_issue)

                # Comment out the line with the error
                if 0 <= line_number - 1 < len(modified_code_lines):
                    # Preserve indentation
                    line_content = modified_code_lines[line_number - 1]
                    if not line_content.strip().startswith('//'):
                        modified_code_lines[line_number - 1] = '// ' + line_content
                else:
                    # Line number out of range
                    break
        except FileNotFoundError as e:
            logger.exception("Verible tool not found.")
            raise HTTPException(status_code=500, detail=f"Verible tool not found: {e}")
        except Exception as e:
            logger.exception("An error occurred during compilation.")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if os.path.exists(filename):
                os.remove(filename)
                logger.info(f"Temporary file {filename} removed.")

        iterations += 1

    return {
        "errors": all_issues,
        "returncode": 1 if all_issues else 0,
        "file_content": code  # Include the original code in the response
    }
