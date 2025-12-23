# Browser Download Agent — PDF Harvester

A compliance-safe, automated agent for harvesting PDF reports from financial institution websites.

## Features
- **Automated Navigation**: Handles cookies, popups, and complex site structures.
- **Compliance Safety**: Respects investor profile gates (Retail/Professional/Institutional) and stops if manual intervention is required.
- **Smart Downloading**: Detects PDF links, "Download" buttons, and fallback candidates.
- **Logging**: Detailed logs and screenshots for debugging and auditing.

## Setup

1.  **Prerequisites**: Python 3.8+
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

## Configuration

Edit `src/config.py` to set your preferences:
- `INVESTOR_PROFILE`: Set to "retail", "professional", "institutional", or "unknown" (default).
- `HEADLESS`: Set to `False` to watch the browser in action.

## Usage

1.  **Prepare Input**:
    Edit `data/input.csv` with the list of institutions and URLs.
    Format: `Institution,URL`

2.  **Run the Agent**:
    ```bash
    python -m src.main
    ```

3.  **Check Results**:
    - **Downloads**: Check the `downloads/` folder.
    - **Logs**: Check `logs/` for execution logs and `logs/screenshots/` for error captures.
    - **Summary**: A CSV summary is saved in `logs/` after each run.

## Project Structure
- `src/`: Source code (`harvester.py`, `config.py`, `utils.py`, `main.py`)
- `data/`: Input files (`input.csv`)
- `downloads/`: Downloaded PDFs
- `logs/`: Execution logs and screenshots
