import os
import subprocess
import re

# ===== CONFIG =====
LLAMA_CLI_PATH = "./llama.cpp/build/bin/llama-cli"
MODEL_PATH = "./llama.cpp/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
SPEC_PATH = "spec.md"
CODE_DIR = "code"
REPORT_PATH = "report.md"
DEBUG_LOG_PATH = "debug.log"
MAX_TOKENS = 2048
MAX_CODE_CHARS = 4000
# ==================

def parse_spec_with_bullets(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    specs = []
    current_title = ""
    current_body = []

    for line in lines:
        if line.startswith("## "):
            if current_title:
                specs.append((current_title, "\n".join(current_body).strip()))
            current_title = line.strip().replace("## ", "")
            current_body = []
        elif line.startswith("* "):
            current_body.append(line.strip("* ").strip())

    if current_title:
        specs.append((current_title, "\n".join(current_body).strip()))

    return specs

def load_code_files():
    code_map = {}

    if os.path.exists(CODE_DIR):
        for fname in os.listdir(CODE_DIR):
            if fname.endswith((".py", ".ts", ".js", ".sol", ".rs")):
                path = os.path.join(CODE_DIR, fname)
                with open(path, "r", encoding="utf-8") as f:
                    code_map[fname] = f.read()[:MAX_CODE_CHARS]

    return code_map

def run_llama(prompt):
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as dbg:
        dbg.write("\n\n========== PROMPT ==========\n")
        dbg.write(prompt + "\n")

    result = subprocess.run([
        LLAMA_CLI_PATH,
        "-m", MODEL_PATH,
        "-p", prompt,
        "-n", str(MAX_TOKENS)
    ], stdout=subprocess.PIPE, text=True)

    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as dbg:
        dbg.write("\n\n========== RESPONSE ==========\n")
        dbg.write(result.stdout + "\n")

    return result.stdout.strip()

def evaluate(specs, code_map):
    matched = 0
    with open(REPORT_PATH, "w", encoding="utf-8") as rep:
        rep.write("# AstarWatch Progress Report (Simplified)\n\n")

        for title, detail in specs:
            found = False

            for fname, code in code_map.items():
                prompt = f"""[QUESTION]
Does the code below implement the specification?

[FORMAT]
Answer only on the first line using: 'Answer: Yes' or 'Answer: No'.

[Specification Title]
{title}

[Details]
{detail}

[Code]
{code}
"""
                answer = run_llama(prompt)

                # 修正された判定ロジック
                first_line = next(
                    (line.strip() for line in answer.splitlines() if line.strip().lower().startswith("answer:")),
                    "No Answer"
                )

                if re.match(r"(?i)^Answer:\s*Yes\b", first_line):
                    matched += 1
                    rep.write(f"- ✅ {title} → `{fname}`\n")
                    found = True
                    break

            if not found:
                rep.write(f"- ❌ {title}\n")

        total = len(specs)
        rep.write(f"\n## ✅ Progress Score: {matched}/{total} ({(matched / total) * 100:.1f}%)\n")

def main():
    if os.path.exists(DEBUG_LOG_PATH):
        os.remove(DEBUG_LOG_PATH)
    if os.path.exists(REPORT_PATH):
        os.remove(REPORT_PATH)

    specs = parse_spec_with_bullets(SPEC_PATH)
    code_map = load_code_files()
    evaluate(specs, code_map)

if __name__ == "__main__":
    main()
