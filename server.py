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

def run_subprocess(command):
    """Run a subprocess command, capturing output in temporary files."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as stdout_file, \
         tempfile.NamedTemporaryFile(mode='w+', delete=False) as stderr_file:
        try:
            result = subprocess.run(
                command,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True
            )
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = stdout_file.read()
            stderr = stderr_file.read()
            return result.returncode, stdout, stderr
        finally:
            os.remove(stdout_file.name)
            os.remove(stderr_file.name)

def parse_errors(output):
    """Parse error messages to extract line numbers and messages."""
    errors = []
    for line in output.splitlines():
        match = re.match(r'^(.*?):(\d+):(\d+): (.*)$', line)
        if match:
            _, line_num, col_num, message = match.groups()
            errors.append({
                "line": int(line_num),
                "column": int(col_num),
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

        # Preprocess the code to handle macros and includes
        preprocess_command = ["verible-verilog-preprocessor", filename]
        preproc_returncode, preproc_stdout, preproc_stderr = run_subprocess(preprocess_command)

        if preproc_returncode != 0:
            logger.error(f"Preprocessing failed with return code {preproc_returncode}.")
            errors = parse_errors(preproc_stderr)
            return {"errors": errors, "returncode": preproc_returncode}

        # Write the preprocessed code to a new temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as preproc_file:
            preproc_file.write(preproc_stdout)
            preproc_filename = preproc_file.name

        # Run Verible lint on the preprocessed code
        lint_command = ["verible-verilog-lint", "--rules=-module-filename", preproc_filename]
        lint_returncode, lint_stdout, lint_stderr = run_subprocess(lint_command)

        logger.info(f"Linting completed with return code {lint_returncode}.")

        # Parse the linting output to extract line numbers and messages
        lint_errors = parse_errors(lint_stdout)

        return {
            "errors": lint_errors,
            "returncode": lint_returncode
        }
    except FileNotFoundError as e:
        logger.exception(f"Required tool not found: {e}")
        raise HTTPException(status_code=500, detail=f"Required tool not found: {e}")
    except Exception as e:
        logger.exception("An error occurred during linting.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary files
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
        if 'preproc_filename' in locals() and os.path.exists(preproc_filename):
            os.remove(preproc_filename)
            logger.info(f"Temporary file {preproc_filename} removed.")

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

        # Preprocess the code to handle macros and includes
        preprocess_command = ["verible-verilog-preprocessor", filename]
        preproc_returncode, preproc_stdout, preproc_stderr = run_subprocess(preprocess_command)

        if preproc_returncode != 0:
            logger.error(f"Preprocessing failed with return code {preproc_returncode}.")
            errors = parse_errors(preproc_stderr)
            return {"errors": errors, "returncode": preproc_returncode}

        # Write the preprocessed code to a new temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sv", delete=False) as preproc_file:
            preproc_file.write(preproc_stdout)
            preproc_filename = preproc_file.name

        # Run Verible's syntax checker on the preprocessed code
        compile_command = ["verible-verilog-syntax", preproc_filename]
        compile_returncode, compile_stdout, compile_stderr = run_subprocess(compile_command)

        logger.info(f"Compilation completed with return code {compile_returncode}.")

        # Parse the compilation output to extract line numbers and messages
        compile_errors = parse_errors(compile_stderr)

        return {
            "errors": compile_errors,
            "returncode": compile_returncode
        }
    except FileNotFoundError as e:
        logger.exception(f"Required tool not found: {e}")
        raise HTTPException(status_code=500, detail=f"Required tool not found: {e}")
    except Exception as e:
        logger.exception("An error occurred during compilation.")
 
