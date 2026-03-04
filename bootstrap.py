#!/usr/bin/env python3
"""
Jarvis Quantum — Local Bootstrap (Python version)
Cross-platform: Windows, macOS, Linux

Usage: python bootstrap.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"


def print_header():
    print(f"\n{BOLD}{BLUE}╔════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}║          JARVIS QUANTUM — LOCAL BOOTSTRAP                      ║{RESET}")
    print(f"{BOLD}{BLUE}║          Quantum AI Project Setup (Sprint 4+)                  ║{RESET}")
    print(f"{BOLD}{BLUE}╚════════════════════════════════════════════════════════════════╝{RESET}\n")


def print_step(num, title):
    print(f"\n{BOLD}{BLUE}{'─' * 70}{RESET}")
    print(f"{BOLD}Step {num}: {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─' * 70}{RESET}")


def run_cmd(cmd, description=""):
    """Run shell command and return success status."""
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if description:
                print(f"  {YELLOW}⚠ {description} (see error above){RESET}")
            return False
        return True
    except Exception as e:
        print(f"  {RED}✗ {description}: {e}{RESET}")
        return False


def check_file_exists(path):
    """Check if file exists."""
    return Path(path).exists()


def main():
    os.chdir(Path(__file__).parent)
    print_header()

    # Step 1: Virtual Environment
    print_step(1, "Creating virtual environment")
    if Path("venv").exists():
        print(f"  {GREEN}✓{RESET} venv/ already exists")
    else:
        if run_cmd([sys.executable, "-m", "venv", "venv"], "Creating venv"):
            print(f"  {GREEN}✓{RESET} venv/ created")
        else:
            print(f"  {RED}✗{RESET} Failed to create venv")
            return False

    # Get Python executable from venv
    if sys.platform == "win32":
        venv_python = str(Path("venv/Scripts/python.exe"))
        venv_pip = str(Path("venv/Scripts/pip.exe"))
    else:
        venv_python = str(Path("venv/bin/python"))
        venv_pip = str(Path("venv/bin/pip"))

    print(f"  {GREEN}✓{RESET} venv activated\n")

    # Step 2: Install dependencies
    print_step(2, "Installing dependencies")
    print("  Upgrading pip...")
    if run_cmd([venv_pip, "install", "--quiet", "--upgrade", "pip", "setuptools", "wheel"]):
        print(f"    {GREEN}✓{RESET} pip/setuptools upgraded")
    
    print("  Installing requirements...")
    if run_cmd([venv_pip, "install", "--quiet", "-r", "requirements.txt"]):
        print(f"  {GREEN}✓{RESET} requirements.txt installed\n")
    else:
        print(f"  {RED}✗{RESET} Failed to install requirements\n")
        return False

    # Step 3: Validate backends
    print_step(3, "Validating quantum backends")
    os.environ["JARVIS_COMPUTE_TIER"] = "local"
    if run_cmd([venv_python, "jarvis_backend_router.py"], "Backend router test"):
        print(f"  {GREEN}✓{RESET} PennyLane + Qiskit + lambeq working\n")
    else:
        print(f"  {YELLOW}⚠ Backend router test had issues{RESET}\n")

    # Step 4: Download datasets
    print_step(4, "Checking datasets")
    
    liar_path = Path("data/liar_train.tsv")
    if liar_path.exists():
        print(f"  {GREEN}✓{RESET} LIAR dataset cached")
    else:
        print(f"  Downloading LIAR dataset (first run, ~30 seconds)...")
        if run_cmd([venv_python, "notebooks/sprint3_task2_liar.py"], "LIAR download"):
            print(f"  {GREEN}✓{RESET} LIAR dataset downloaded\n")
        else:
            print(f"  {YELLOW}⚠ LIAR download incomplete{RESET}\n")
    
    clinc_path = Path("data/clinc150_full.json")
    if clinc_path.exists():
        print(f"  {GREEN}✓{RESET} CLINC150 dataset cached\n")
    else:
        print(f"  {YELLOW}ℹ  Run: python notebooks/sprint3_task1_clinc150.py to download CLINC150{RESET}\n")

    # Step 5: Train models
    print_step(5, "Training credibility module")
    
    classical_model = Path("modules/credibility/models/classical_credibility.pkl")
    quantum_model = Path("modules/credibility/models/quantum_credibility.pt")
    
    if classical_model.exists() and quantum_model.exists():
        print(f"  {GREEN}✓{RESET} Models already trained\n")
    else:
        print(f"  Training (this will take 5-10 minutes)...\n")
        orig_dir = os.getcwd()
        os.chdir("modules/credibility")
        if run_cmd([venv_python, "train_all.py"], "Model training"):
            os.chdir(orig_dir)
            print(f"  {GREEN}✓{RESET} Models trained and saved\n")
        else:
            os.chdir(orig_dir)
            print(f"  {YELLOW}⚠ Training incomplete (run manually: cd modules/credibility && python train_all.py){RESET}\n")

    # Final summary
    print(f"{BOLD}{BLUE}╔════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}║                    ✅ SETUP COMPLETE                           ║{RESET}")
    print(f"{BOLD}{BLUE}╚════════════════════════════════════════════════════════════════╝{RESET}\n")

    print(f"{BOLD}📋 NEXT STEPS:{RESET}\n")
    print(f"  {BOLD}1️⃣  Start the API gateway (routes to all modules):{RESET}")
    print(f"     {YELLOW}python modules/gateway/service.py{RESET}\n")

    print(f"  {BOLD}2️⃣  In another terminal, start services:{RESET}")
    print(f"     {YELLOW}cd modules/credibility && python service.py{RESET}")
    print(f"     (or use docker-compose up)\n")

    print(f"  {BOLD}3️⃣  Test the system:{RESET}")
    print(f"     {YELLOW}curl http://localhost:3030/api/quantum/status{RESET}\n")

    print(f"  {BOLD}4️⃣  Try a credibility check:{RESET}")
    print(f"     {YELLOW}curl -X POST http://localhost:3031/api/credibility/verify \\{RESET}")
    print(f"     {YELLOW}  -H 'Content-Type: application/json' \\{RESET}")
    print(f"     {YELLOW}  -d '{{\"claim\": \"The Earth is round\"}}{RESET}'\n")

    print(f"{BOLD}📖 Documentation:{RESET}")
    print(f"   • Full setup guide: {YELLOW}STARTUP.md{RESET}")
    print(f"   • Sprint summary: {YELLOW}docs/sprint_1_3_summary.md{RESET}")
    print(f"   • QPU setup: {YELLOW}docs/qpu_setup_guide.md{RESET}\n")

    print(f"{BOLD}🎯 Quick Reference:{RESET}")
    print(f"   Gateway:      http://localhost:3030/api/quantum/status")
    print(f"   Credibility:  http://localhost:3031/docs (Swagger UI)")
    print(f"   Search:       http://localhost:3033/docs")
    print(f"   Compute tier: export JARVIS_COMPUTE_TIER=local|cloud-gpu|cloud-qpu\n")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Setup cancelled by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)
