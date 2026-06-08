# Roadmap

The first release focuses on Markdown because it has simple, inspectable image
references and is easy to validate non-destructively.

Planned directions:

- richer Markdown parsing for edge cases such as nested parentheses
- HTML input and output rewriting
- document adapters for formats such as DOCX or exported HTML bundles
- optional OpenCV inpainting fallback for lightweight local use
- mask preview and editing workflows
- structured JSON run reports

The project will keep the same safety boundary: only process images that the
user owns or is authorized to modify.
