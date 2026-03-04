# Jarvis Quantum — QPU Account Setup Guide
**Task 1.6: IBM Quantum + Amazon Braket**
**Generated:** 02 March 2026

---

## 1. IBM Quantum (Free Tier)

### Sign Up
1. Go to https://quantum.ibm.com
2. Click "Create an IBMid account" (or sign in with existing IBM/Google/GitHub)
3. Complete the registration form
4. Verify your email

### What You Get (Free)
- Access to 127-qubit Eagle processors (ibm_brisbane, ibm_osaka, etc.)
- 10 minutes of QPU time per month
- Unlimited simulator access
- Qiskit Runtime for optimised circuit execution

### Get Your API Token
1. Log in to https://quantum.ibm.com
2. Click your profile icon (top right) > "Account settings"
3. Copy your API token
4. Save it to your config:
```bash
# Add to jarvis-quantum/config/cloud-qpu.env
IBM_QUANTUM_TOKEN=your_token_here
IBM_QUANTUM_INSTANCE=ibm-q/open/main
```

### Test Connection
```python
# notebooks/test_ibm_quantum.py
from qiskit_ibm_runtime import QiskitRuntimeService

# First time only — saves credentials locally
QiskitRuntimeService.save_account(
    channel="ibm_quantum",
    token="YOUR_TOKEN_HERE",
    overwrite=True
)

service = QiskitRuntimeService(channel="ibm_quantum")
print("Available backends:")
for backend in service.backends():
    print(f"  {backend.name}: {backend.num_qubits} qubits, status={backend.status().operational}")
```

### Install Required Package
```powershell
pip install qiskit-ibm-runtime
```

### Running a Circuit on Real Hardware
```python
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

service = QiskitRuntimeService(channel="ibm_quantum")
backend = service.least_busy(operational=True, simulator=False)
print(f"Using: {backend.name} ({backend.num_qubits} qubits)")

# Bell state circuit
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()

# Run with Sampler
sampler = SamplerV2(mode=backend)
job = sampler.run([qc], shots=1024)
result = job.result()
print(result[0].data.meas.get_counts())
# Expected: roughly {'00': ~512, '11': ~512}
```

### Jarvis Integration (Backend Router Update)
```python
# Add to jarvis_backend_router.py
def get_ibm_backend(self, n_qubits):
    from qiskit_ibm_runtime import QiskitRuntimeService
    service = QiskitRuntimeService(channel="ibm_quantum")
    backend = service.least_busy(
        operational=True,
        simulator=False,
        min_num_qubits=n_qubits
    )
    return backend
```

---

## 2. Amazon Braket (Free Tier)

### Sign Up
1. Go to https://aws.amazon.com and create an AWS account (if you don't have one)
2. You'll need a credit card (won't be charged for free tier)
3. Go to https://console.aws.amazon.com/braket
4. Click "Get started" to enable Amazon Braket in your account

### What You Get (Free)
- $750 in free credits for quantum computing (AWS Free Tier)
- Access to IonQ Aria (25 qubits, trapped ion)
- Access to Rigetti Aspen-M (80 qubits, superconducting)
- Access to IQM Garnet (20 qubits, superconducting)
- Unlimited local simulator
- 1 hour free SV1 simulator per month

### Set Up Credentials
```powershell
pip install amazon-braket-sdk boto3

# Configure AWS CLI (one-time)
pip install awscli
aws configure
# Enter: AWS Access Key ID, Secret Key, Region (us-east-1), Output (json)
```

### Get AWS Keys
1. Go to https://console.aws.amazon.com/iam
2. Users > Your user > Security credentials
3. Create access key > CLI use case
4. Save Access Key ID and Secret Access Key
```bash
# Add to jarvis-quantum/config/cloud-qpu.env
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_DEFAULT_REGION=us-east-1
BRAKET_SPENDING_LIMIT=5.00
```

### Test Connection
```python
# notebooks/test_braket.py
from braket.aws import AwsDevice
from braket.circuits import Circuit

# List available QPUs
for arn in AwsDevice.get_devices(types=["QPU"]):
    print(f"  {arn.name}: {arn.properties.paradigm.qubitCount} qubits ({arn.provider_name})")

# Bell state on local simulator
circ = Circuit().h(0).cnot(0, 1)
from braket.devices import LocalSimulator
sim = LocalSimulator()
result = sim.run(circ, shots=1024).result()
print(result.measurement_counts)
# Expected: {'00': ~512, '11': ~512}
```

### Running on Real QPU (IonQ)
```python
from braket.aws import AwsDevice
from braket.circuits import Circuit

# IonQ Aria
ionq = AwsDevice("arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1")

circ = Circuit().h(0).cnot(0, 1)
task = ionq.run(circ, shots=100)  # Keep shots low to save credits
result = task.result()
print(result.measurement_counts)
```

### Braket Cost Control
```python
# Set up billing alerts
# Go to: AWS Console > Billing > Budgets > Create budget
# Set: $5/month alert for Braket spending
#
# QPU pricing (approximate):
#   IonQ Aria:    $0.03 per task + $0.01 per shot
#   Rigetti:      $0.03 per task + $0.00035 per shot
#   SV1 simulator: $0.075 per minute (1hr free/month)
```

### Jarvis Integration
```python
# Add to jarvis_backend_router.py
def get_braket_backend(self, n_qubits, provider='ionq'):
    from braket.aws import AwsDevice
    devices = {
        'ionq': "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1",
        'rigetti': "arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3",
        'iqm': "arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet",
    }
    return AwsDevice(devices[provider])
```

---

## 3. Recommended Setup Order

### Step 1: IBM Quantum (do first — easier)
1. Sign up at quantum.ibm.com
2. pip install qiskit-ibm-runtime
3. Save your token
4. Run test_ibm_quantum.py
5. Verify you can see available backends

### Step 2: Amazon Braket (do second — needs AWS account)
1. Create/sign in to AWS account
2. Enable Braket in console
3. pip install amazon-braket-sdk boto3 awscli
4. Configure AWS credentials
5. Run test_braket.py with LocalSimulator first
6. Set up $5 spending alert before touching real QPUs

### Step 3: Update Backend Router
1. Add IBM and Braket backends to jarvis_backend_router.py
2. Add tokens to config/cloud-qpu.env
3. Add cloud-qpu.env to .gitignore (NEVER commit tokens)
4. Test tier switching: local -> cloud-sim -> cloud-qpu

### Step 4: First Real QPU Run (Sprint 5)
1. Run Tutorial 1 Bell state on IBM Eagle
2. Run Tutorial 1 Bell state on IonQ Aria
3. Compare: sim results vs QPU results (noise analysis)
4. This validates the full pipeline before running NLU circuits

---

## 4. Security Reminders

- NEVER commit API tokens to git
- Add config/cloud-qpu.env to .gitignore
- Consider migrating all tokens to HashiCorp Vault (your existing plan)
- Set spending limits on AWS Braket before enabling QPU access
- IBM free tier has a 10-minute monthly limit — plan circuit runs carefully
- Use simulators for development, QPU only for validation runs

---

## 5. Token Checklist

| Service | Token | Status |
|---------|-------|--------|
| IBM Quantum | IBM_QUANTUM_TOKEN | [ ] Set up |
| AWS Access Key | AWS_ACCESS_KEY_ID | [ ] Set up |
| AWS Secret Key | AWS_SECRET_ACCESS_KEY | [ ] Set up |
| Google Gemini | GEMINI_API_KEY | [x] Exists (REGENERATE - was exposed) |
