# vaice-sentinel-lite

Een verzameling prompt engineering-artefacten voor het implementeren van robuuste AI-guardrails. Deze toolkit biedt praktische voorbeelden en templates die ontwikkelaars helpen te waarborgen dat hun AI-systemen voldoen aan de EU AI Act.

Prompt Engineering-artefacten (Apache-2.0)

# prompt engineering artifacts (apache-2.0)

## doel
deze repo publiceert **niet-uitvoerbare** prompt artefacten (teksten, templates, schema’s) onder **apache-2.0** voor versiebeheer, hergebruik en audit.

## gebruik
- prompts zijn tekst/specificatie; **geen code** om te runnen.
- hergebruik toegestaan onder apache-2.0 (inclusief patent-clausule).
- indien je deze prompts inzet in systemen, borg zelf compliance en kwaliteitscontrole.

## inhoud
- `prompts/*.yaml` — versieerbare prompts met metadata
- `schemas/prompt.schema.json` — formaatdefinitie voor validatie
- ci valideert alleen structuur/regels; er wordt niets uitgevoerd.

## waarom apache-2.0 voor prompts?
- duidelijke gebruiksrechten + **patent grant** → beschermt tegen reverse patenting / patent trolling op prompt-artefacten.
- expliciete **notice**-keten en licentieheaders.

## quick start
```bash
# validatie lokaal (node jq optioneel)
npm i -g ajv-cli
ajv validate -s schemas/prompt.schema.json -d 'prompts/*.yaml' --spec=draft2020
