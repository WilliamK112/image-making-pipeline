# Image Making Pipeline

![Dashboard Preview](assets/dashboard-preview.png)

Local image generation workspace with:
- Prompt studio + batch gallery UI
- Local one-click runner service (`local_runner_server.py`)
- Batch metadata + per-variant metadata
- OpenAI provider adapter (extensible)

## Run local runner

```bash
export OPENAI_API_KEY="YOUR_KEY"
python3 local_runner_server.py
```

## Run pipeline directly

```bash
python3 trex_image_pipeline.py --count 4
# or
python3 trex_image_pipeline.py --request-file ~/Downloads/studio_request.json
```

## Architecture Overview

This project follows a modular structure with clear separation between interface, execution logic, and outputs/artifacts. The exact implementation details vary by repository, but the intent is to keep core logic testable and easy to extend.


## Project Structure

```text
.
├─ src/            # Core source code (if present)
├─ public/         # Static assets / UI resources (if present)
├─ docs/           # Documentation and notes (if present)
├─ scripts/        # Utility scripts (if present)
├─ test/           # Tests (if present)
└─ README.md       # Project overview
```

> Folder names vary by project; this section describes the intended organization pattern.


## Quick Start

1. Clone the repository
2. Install dependencies (if any)
3. Run the project using its local start/build instructions

If this repo is a library or static project, refer to scripts/config files for exact commands.


## Current Scope

This repository reflects the project’s current implementation and active direction. Planned improvements are tracked through issues/commits and may evolve over time.

