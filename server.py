from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import uuid
import os
import re

app = FastAPI()

class CodeSubmission(BaseModel):
    code: str

@app.post("/lint")
async def lint_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="No code provided.")
    
    # Extract module name using regex
    match = re.search(r'\bmodule\s+(\w+)', code)
    if not match:
        raise HTTPException(status_code=400, detail="No module declaration found.")
    
    # Sanitize module name to create a valid filename
    module_name = re.sub(r'\W+', '_', match.group(1))
    filename = f"/tmp/{module_name}.sv"
    
    try:
        # Write the code to a temporary file
        with open(filename, "w") as f:
            f.write(code + "\n")  # Ensure the file ends with a newline
        
        # Run Verible lint with the 'module-filename' rule disabled
        result = subprocess.run(
            ["verible-verilog-lint", "--rules=all", "--rules-exclude=module-filename", filename],
            capture_output=True,
            text=True
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Verible linter not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compile")
async def compile_code(payload: LintRequest):
    code = payload.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="No code provided.")
    
    # Extract module name using regex
    match = re.search(r'\bmodule\s+(\w+)', code)
    if not match:
        raise HTTPException(status_code=400, detail="No module declaration found.")
    
    module_name = match.group(1)
    filename = f"/tmp/{module_name}.sv"
    
    try:
        # Write the code to a temporary file
        with open(filename, "w") as f:
            f.write(code + "\n")  # Ensure the file ends with a newline
        
        # Run Verible's syntax checker (verible-verilog-parse)
        result = subprocess.run(
            ["verible-verilog-parse", filename],
            capture_output=True,
            text=True
        )
        
        # Determine if syntax is correct based on return code
        if result.returncode == 0:
            return {
                "stdout": "Syntax check passed.",
                "stderr": "",
                "returncode": 0
            }
        else:
            return {
                "stdout": "",
                "stderr": result.stderr,
                "returncode": 1
            }
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Verible parser not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
