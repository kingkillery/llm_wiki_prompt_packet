@echo off
cd /d "C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet"
:loop
C:\Python314\python.exe scripts\wiki_auto_update.py --verbose >> .artifacts\auto_update.log 2>&1
timeout /t 300 /nobreak >nul
goto loop
