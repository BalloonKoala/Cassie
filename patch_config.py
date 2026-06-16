#!/usr/bin/env python3
import sys
from pathlib import Path
import yaml
DEFAULTS = {"sample_rate":48000,"channels":1,"chunk_size":1024,"input_device_index":None,"output_device_index":None}
def patch(path):
    p = Path(path)
    if not p.is_file(): return
    cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    audio = cfg.setdefault("audio", {})
    for k,v in DEFAULTS.items():
        if k not in audio or audio.get(k) == 1:
            audio[k] = v
    p.write_text(yaml.dump(cfg, default_flow_style=False, sort_keys=False), encoding="utf-8")
    print("Config patched:", p)
if __name__=="__main__":
    patch(sys.argv[1] if len(sys.argv)>1 else "/opt/cassie/config/config.yaml")