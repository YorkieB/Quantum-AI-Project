#!/bin/bash

# Jarvis Quantum — Local Bootstrap Script
# ==========================================
# One-command setup for development environment
# Usage: bash bootstrap.sh
# or (Windows): python bootstrap.py

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          JARVIS QUANTUM — LOCAL BOOTSTRAP                      ║"
echo "║          Quantum AI Project Setup (Sprint 4+)                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Virtual Environment
echo "📦 Step 1: Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ✓ venv/ already exists"
else
    python -m venv venv
    echo "   ✓ venv/ created"
fi

# Activate venv
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
echo "   ✓ venv activated"
echo ""

# Step 2: Install dependencies
echo "📚 Step 2: Installing dependencies..."
pip install --quiet --upgrade pip setuptools wheel
echo "   ✓ pip/setuptools upgraded"

pip install --quiet -r requirements.txt
echo "   ✓ requirements.txt installed"
echo ""

# Step 3: Validate backends
echo "🔧 Step 3: Validating quantum backends..."
export JARVIS_COMPUTE_TIER=local
python jarvis_backend_router.py > /tmp/backend_test.log 2>&1 && \
    echo "   ✓ PennyLane + Qiskit working" || \
    echo "   ⚠ Backend router test had issues (see /tmp/backend_test.log)"
echo ""

# Step 4: Download datasets
echo "📥 Step 4: Downloading datasets (LIAR + CLINC150)..."
if [ -f "data/liar_train.tsv" ]; then
    echo "   ✓ LIAR dataset cached"
else
    python notebooks/sprint3_task2_liar.py > /tmp/download_liar.log 2>&1 && \
        echo "   ✓ LIAR dataset downloaded" || \
        echo "   ⚠ LIAR download incomplete (see /tmp/download_liar.log)"
fi

if [ -f "data/clinc150_full.json" ]; then
    echo "   ✓ CLINC150 dataset cached"
else
    echo "   ℹ Run: python notebooks/sprint3_task1_clinc150.py to download CLINC150"
fi
echo ""

# Step 5: Train models
echo "🚀 Step 5: Training credibility module..."
echo "   (This will take 5-10 minutes...)"

if [ -f "modules/credibility/models/classical_credibility.pkl" ] && \
   [ -f "modules/credibility/models/quantum_credibility.pt" ]; then
    echo "   ✓ Models already trained"
else
    cd modules/credibility
    python train_all.py > /tmp/train_models.log 2>&1 && \
        echo "   ✓ Models trained and saved" || \
        echo "   ⚠ Training incomplete (see /tmp/train_models.log)"
    cd ../..
fi
echo ""

# Step 6: Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ SETUP COMPLETE                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 NEXT STEPS:"
echo ""
echo "  1️⃣  Start the API gateway (routes to all modules):"
echo "     python modules/gateway/service.py"
echo ""
echo "  2️⃣  In another terminal, start individual services:"
echo "     # Terminal 2"
echo "     cd modules/credibility && python service.py"
echo "     "
echo "     # Terminal 3"
echo "     cd modules/Search && python service.py"
echo ""
echo "  3️⃣  Test the system:"
echo "     curl http://localhost:3030/api/quantum/status"
echo ""
echo "  4️⃣  Try a credibility check:"
echo "     curl -X POST http://localhost:3031/api/credibility/verify \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"claim\": \"The Earth is round\"}'"
echo ""
echo "📖 Full documentation: see STARTUP.md"
echo ""
echo "🎯 Quick reference:"
echo "   Gateway:   http://localhost:3030/api/quantum/status"
echo "   Credibility: http://localhost:3031/docs (Swagger UI)"
echo "   Search:    http://localhost:3033/docs"
echo "   Compute tier: export JARVIS_COMPUTE_TIER=local|cloud-gpu|cloud-qpu"
echo ""
echo "Logs saved to:"
echo "  /tmp/backend_test.log"
echo "  /tmp/download_liar.log"
echo "  /tmp/train_models.log"
echo ""
