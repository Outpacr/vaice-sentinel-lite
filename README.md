# vaice-sentinel-lite
A collection of prompt engineering artefacts for implementing robust AI guardrails. This toolkit provides practical examples and templates to help developers ensure their AI systems are compliant with the EU AI Act.

Prompt Engineering Artifacts (Apache-2.0)
Purpose
This repo publishes non-executable prompt artifacts (texts, templates, schemas) under the Apache-2.0 license for version control, reuse, and auditing.

Usage
Prompts are text/specifications; they are not code to be executed.

Reuse is permitted under Apache-2.0 (including its patent clause).

If you use these prompts in your systems, you are responsible for ensuring your own compliance and quality control.

Contents
prompts/*.yaml — Versionable prompts with metadata

schemas/prompt.schema.json — Format definition for validation

The CI only validates structure/rules; nothing is executed.

Why Apache-2.0 for Prompts?
Clear usage rights + patent grant → Protects against reverse patenting / patent trolling on prompt artifacts.

Explicit NOTICE chain and license headers.

Quick Start
Bash

# Validate locally (node, jq optional)
npm i -g ajv-cli
ajv validate -s schemas/prompt.schema.json -d 'prompts/*.yaml' --spec=draft2020
