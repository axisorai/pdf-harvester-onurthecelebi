import os
import pandas as pd
from datetime import datetime
from . import config
from . import utils
from .harvester import PdfHarvester

def main():
    # 1. Setup
    logger = utils.setup_logging()
    logger.info("Starting PDF Harvester Agent...")
    
    # 2. Load Input
    input_path = os.path.join(config.DATA_DIR, "input.csv")
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return

    try:
        df = pd.read_csv(input_path)
        if "Institution" not in df.columns or "URL" not in df.columns:
            logger.error("Input CSV must contain 'Institution' and 'URL' columns.")
            return
    except Exception as e:
        logger.error(f"Failed to read input CSV: {e}")
        return

    # 3. Initialize Harvester
    harvester = PdfHarvester()
    harvester.start()
    
    results = []

    # 4. Process URLs
    try:
        for index, row in df.iterrows():
            institution = row["Institution"]
            url = row["URL"]
            
            if pd.isna(url) or not url.strip():
                continue
                
            logger.info(f"--- Processing {index + 1}/{len(df)}: {institution} ---")
            
            result = harvester.process_url(institution, url)
            results.append({
                "Institution": institution,
                "Start_URL": result["start_url"],
                "Final_URL": result["final_url"],
                "Status": result["status"],
                "Notes": result["notes"],
                "File_Path": result["file_path"],
                "Timestamp": datetime.now().isoformat()
            })
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
    finally:
        harvester.stop()

    # 5. Save Summary
    output_path = os.path.join(config.LOG_DIR, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    pd.DataFrame(results).to_csv(output_path, index=False)
    logger.info(f"Summary saved to {output_path}")
    logger.info("Harvesting complete.")

if __name__ == "__main__":
    main()
