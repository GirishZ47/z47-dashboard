@echo off
echo Starting Z47 Index Dashboard...
"C:\Users\Girish Shenoy\AppData\Local\Programs\Python\Python312\Scripts\streamlit.exe" run "%~dp0app.py" --server.port 8501
pause
