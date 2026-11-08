Save this as a skill called "Lean Input". Use it before you read anything big.

## THE GOAL
Do the same job, but send less text into this chat. Never read a raw dump when a free tool can cut it down first.

# SET UP (once)
Run `pip install trafilatura duckdb docling changedetection.io tenacity pydantic`
Install `jq`, `ripgrep` and `RTK` from their official releases.

If a tool is missing, install it first, then carry on.

## THE 9 RULES
1. A web page link: get clean text with trafilatura, not the raw HTML.
`trafilatura -u "URL" --output-format txt`

2. JSON or an API reply: pull only the fields the job needs with jq.
`curl -s "URL" | jq '{name, price}'`

3. A folder of files: search first with ripgrep, then read only the lines that match.
`rg -n "word" folder/`

4. A CSV or spreadsheet: load it in DuckDB and ask one SQL question. Read only the result.
`SELECT col, count(*) FROM 'file.csv' GROUP BY col`

5. A PDF or Word file: turn it into markdown with Docling first.
`docling convert file.pdf --to md`

6. A page I want watched: track it with changedetection.io. Read only the change, never the whole page again.

7. Long command output (git, tests, logs): run it through RTK so the output is short.
`rtk git log -n 30`

8. A flaky API: retry the call in code with Tenacity. Do not redo the whole job in chat.

9. A structured answer: check it with a Pydantic model in code. If it fails, fix only the fields that failed.

## HOW TO REPORT
- Each time you cut something, tell me the size before and after, in characters.
- If a tool might drop something the job needs, say so and use the full text for that part.
- Never make up numbers.
