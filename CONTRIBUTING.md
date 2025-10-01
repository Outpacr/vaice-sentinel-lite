```md
# contributing
- lever alle prompts aan als `*.yaml` conform `schemas/prompt.schema.json`.
- voeg bovenaan elk bestand de apache-2.0 header toe.
- geen binaires, geen model-weights, geen secrets.
- prs moeten de linter en schema-checks passeren; er draait **geen** runtime test.

commit conventie (kort):
- `feat(prompt): ...` nieuwe prompt
- `fix(prompt): ...` correctie
- `docs: ...` documentatie
