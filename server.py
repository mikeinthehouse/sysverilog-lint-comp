from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import uuid
import os

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
