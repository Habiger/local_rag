

Notes:
- page wise docling conversion due to docling failing on very large files #TODO: reference github issues
- 

# Installation Notes

## Dependency Conflicts
`docling-serve` is installed manually with `--no-deps` because its dependency constraints conflict with `pydantic-ai` (Pydantic version resolution issues).

Install it after setting up the environment:

```bash
uv sync
uv pip install --no-deps docling-serve==1.16.1
```
## Model Files
/model folder
# Design Decisions
https://www.cosmicpython.com/book/chapter_02_repository.html
maybe i should get: 99 Bottles of OOP by Sandi Metz

## Pagewise Docling Conversion
Reasons:
* Docling has unresolved issues with large pdf files; see also: 
    * https://github.com/docling-project/docling/issues/1283
    * https://github.com/docling-project/docling/issues/1654
* Utilizing multiple docling-serve instances - each instance with a serperate dedicated GPU - to parallelize pdf processing to improve conversion speed

# Alternatives
https://github.com/duckling-ui/duckling/tree/main