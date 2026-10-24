"""Re-run the whole pipeline after updating the Excel file:  python run_all.py"""
import subprocess
import sys

for step in ["01_clean_data.py", "02_eda_tests.py", "03_forecast_models.py", "04_whatif_model.py",
             "05_long_horizon.py", "06_export_web_data.py"]:
    print(f"\n===== {step} =====", flush=True)
    subprocess.run([sys.executable, step], check=True)
print("\nDone. Website data updated in web/public/data/site.json (preview: cd web && npm run dev)")
