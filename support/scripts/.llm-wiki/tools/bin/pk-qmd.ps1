#!/usr/bin/env pwsh
& node "C:\dev\Desktop-Projects\llm_wiki_prompt_packet\llm_wiki_prompt_packet\support\scripts\.llm-wiki\tools\pk-qmd\dist\cli\qmd.js" @args
exit $LASTEXITCODE
