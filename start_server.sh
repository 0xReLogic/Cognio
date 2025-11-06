#!/bin/bash
cd /workspaces/Cognio
/home/codespace/.python/current/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8080 --reload
