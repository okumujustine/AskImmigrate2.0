#!/bin/bash

# Run backend on port 8088
uvicorn backend.code.api:app --host 0.0.0.0 --port 8088 &

# Run frontend on port 4044
cd frontend && npm run dev -- --port 4044
