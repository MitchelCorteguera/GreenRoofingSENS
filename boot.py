# boot.py - Minimal boot for Pico W
import gc
import machine

# Basic garbage collection
gc.collect()

print("[Boot] Ready - main.py will handle the rest")