from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import uuid
import os
import re

app = FastAPI()

class CodeSubmission(BaseModel):
    code: str

@app.post("/lint")
async def lint_code(submission: CodeSubmission):
    temp_filename = f"/tmp/{uuid.uuid4()}.sv"
    try:
        # Save the code to a temporary file
        with open(temp_filename, 'w') as temp_file:
            temp_file.write(submission.code)

        # Run Verible linter
        result = subprocess.run(
            ["verible-verilog-lint", temp_filename],
            capture_output=True,
            text=True
        )

        # Return the linter output
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

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
