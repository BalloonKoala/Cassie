#!/usr/bin/env python3
"""List PyAudio devices — run on Pi: /opt/cassie/venv/bin/python3 find_devices.py"""
import pyaudio

pa = pyaudio.PyAudio()
print("Input devices:")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info.get("maxInputChannels", 0) > 0:
        print(f"  [{i}] {info['name']}")

print("\nOutput devices:")
for i in range(pa.get_device_count()):
    info = pa.get_device_info_by_index(i)
    if info.get("maxOutputChannels", 0) > 0:
        print(f"  [{i}] {info['name']}")

pa.terminate()
