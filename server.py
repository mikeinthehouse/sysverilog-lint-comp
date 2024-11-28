from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import re
import logging
import os

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
    
    # Sanitize module name to create a valid filename
    module_name = re.sub(r'\W+', '_', match.group(1))
    filename = f"/tmp/{module_name}.sv"
    
    try:
        # Write the code to a temporary file
        with open(filename, "w") as f:
            f.write(code + "\n")  # Ensure the file ends with a newline
        
        logger.info(f"Linting file: {filename}")
        
        # Run Verible lint with the 'module-filename' rule disabled
        result = subprocess.run(
            ["verible-verilog-lint", "--rules=all", "--rules-exclude=module-filename", filename],
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
    
    # Extract module name using regex
    match = re.search(r'\bmodule\s+(\w+)', code)
    if not match:
        logger.error("No module declaration found.")
        raise HTTPException(status_code=400, detail="No module declaration found.")
    
    # Sanitize module name to create a valid filename
    module_name = re.sub(r'\W+', '_', match.group(1))
    filename = f"/tmp/{module_name}.sv"
    
    try:
        # Write the code to a temporary file
        with open(filename, "w") as f:
            f.write(code + "\n")  # Ensure the file ends with a newline
        
        logger.info(f"Compiling file: {filename}")
        
        # Run Verible's syntax checker (verible-verilog-parse)
        result = subprocess.run(
            ["verible-verilog-parse", filename],
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
        logger.exception("Verible parser not found.")
        raise HTTPException(status_code=500, detail="Verible parser not found.")
    except Exception as e:
        logger.exception("An error occurred during compile checking.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the temporary file
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"Temporary file {filename} removed.")
