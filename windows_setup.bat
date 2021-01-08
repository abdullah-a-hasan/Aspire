python -m venv asp-env
call asp-env\Scripts\activate.bat
pip install wheel==0.36.2
pip install -r apsire_web_app\requirements.txt
pip install -r aspire_aligner\requirements.txt