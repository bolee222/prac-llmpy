from __future__ import annotations


def json2diagram(payload: dict) -> str:
    entities = payload.get("entities", [])
    relationship = payload.get("relationship", {})

    if len(entities) < 2:
        return "Diagram unavailable: missing entities."

    source = entities[0]
    target = entities[1]
    label = relationship.get("type", "related").replace(" ", "_")
    direction = relationship.get("direction", "bidirectional")

    if direction == "image_2_to_image_1":
        source, target = target, source

    if direction == "bidirectional":
        connector = "<-->"
    else:
        connector = "-->"

    return (
        "flowchart LR\n"
        f"  {source['id']}[{source['label']}] {connector} {target['id']}[{target['label']}]:::{label}\n"
        f"  classDef {label} fill:#2563eb,color:#fff;\n"
    )
