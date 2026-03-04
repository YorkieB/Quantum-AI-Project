#!/usr/bin/env python3
"""Test Amazon Braket connection."""

# Step 1: Install
# pip install amazon-braket-sdk boto3

# Step 2: Configure AWS credentials
# aws configure (enter your keys)

from braket.circuits import Circuit
from braket.devices import LocalSimulator

# Test local simulator first (free, no AWS needed)
print("Testing Braket local simulator...")
circ = Circuit().h(0).cnot(0, 1)
sim = LocalSimulator()
result = sim.run(circ, shots=1024).result()
counts = result.measurement_counts
print(f"  Bell state results: {counts}")
print(f"  Expected: ~50/50 split between 00 and 11")

# Test AWS connection (needs credentials)
try:
    from braket.aws import AwsDevice
    print("\nAvailable QPU devices:")
    for device in AwsDevice.get_devices(types=["QPU"]):
        print(f"  {device.name}: {device.provider_name} | "
              f"qubits: {device.properties.paradigm.qubitCount} | "
              f"status: {device.status}")
    print("\nAmazon Braket setup complete!")
except Exception as e:
    print(f"\nAWS connection not configured yet: {e}")
    print("Run 'aws configure' with your access keys first.")
    print("Local simulator works fine for now.")
