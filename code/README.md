## Project Title

Modeling Longitudinal Learning Dynamics Using Markov Models


## Student attribution

| Name          | Roll No             | Project title                                               |
|---------------|---------------------|-------------------------------------------------------------|
| ATHAR HUSSAIN | `F22BINFT1M01231`   | Modeling Longitudinal Learning Dynamics Using Markov Models |



## Problem Statement

Weekly engagement indicators evolve over the course of a semester, and a single static score is therefore insufficient to characterize how a student progresses. This Final Year Project presents a Python-based system that discovers latent engagement states from longitudinal data, composes these states into learner trajectories, and enables interactive trajectory exploration through a browser-based dashboard.

## Core Idea

The methodology follows the VaSSTra approach, progressing from raw variables to discrete states and finally to learner trajectories.

- **Source data:** a local copy of `LongitudinalEngagement.csv`.
- **Analytical pipeline:** course-wise standardization, Gaussian-mixture state discovery, and trajectory clustering, implemented in Python.
- **User interface:** a web dashboard that accepts manual state-sequence input for trajectory testing.

## Run Instructions

### Primary launcher

From PowerShell:

```powershell
.\run\run_project.ps1
```

This is the recommended one-step launcher. It refreshes the backend artifacts, starts the project-local web server, and opens the dashboard automatically.

Two optional switches are available: `-SkipBackend` reuses the existing artifacts, and `-NoBrowser` starts the local server without opening a browser window.

For a double-click launcher in File Explorer, use `run\run_project.bat`.

### Other launchers

- `run\run_backend.ps1` or `run\run_backend.bat`: regenerate backend artifacts only.
- `run\run_frontend.ps1` or `run\run_frontend.bat`: serve the frontend only.
- `run\run_notebook.ps1` or `run\run_notebook.bat`: open the Python VaSSTra notebook (`notebook/vasstra_python.ipynb`) in JupyterLab.