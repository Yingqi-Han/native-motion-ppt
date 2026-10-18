#!/usr/bin/env python3
"""Validate the portable skill's entrypoint, references, schema and sources."""
import ast,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 errors=[]
 text=(ROOT/"SKILL.md").read_text(encoding="utf-8")
 if not text.startswith("---\n"):errors.append("Missing skill front matter")
 else:
  front=text.split("---",2)[1]
  if not re.search(r"^name: native-motion-ppt$",front,re.M):errors.append("Invalid skill name")
  desc=re.search(r"^description: (.+)$",front,re.M)
  if not desc or len(desc[1])>1024:errors.append("Invalid description")
 for reference in re.findall(r"\]\(([^)]+)\)",text):
  if "://" not in reference and not (ROOT/reference).is_file():errors.append("Missing reference: "+reference)
 required=["agents/openai.yaml","assets/spec.schema.json","examples/demo.json","examples/minimal.json","assets/fonts/SpaceGrotesk-SemiBold.ttf",
 "assets/remotion/src/index.tsx","scripts/motion_ppt.py","scripts/nmp.py","scripts/install_skill.py","requirements-core.txt",
 "references/first-project.md","examples/starter-minimal.json","examples/product-intro.json","examples/project-update.json","README.md","LICENSE"]
 for path in required:
  if not (ROOT/path).is_file():errors.append("Missing "+path)
 for p in (ROOT/"scripts").rglob("*.py"):
  try:ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
  except SyntaxError as e:errors.append(str(e))
 from jsonschema import Draft202012Validator
 schema=json.loads((ROOT/"assets/spec.schema.json").read_text());Draft202012Validator.check_schema(schema)
 sys.path.insert(0,str(ROOT/"scripts"));from native_motion.model import load
 for p in (ROOT/"examples").glob("*.json"):
  try:load(p)
  except ValueError as e:errors.append(str(p)+": "+str(e))
 print(json.dumps({"name":"native-motion-ppt","valid":not errors,"errors":errors},ensure_ascii=False,indent=2))
 if errors:sys.exit(1)
if __name__=="__main__":main()

