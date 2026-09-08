
# Introduction
The motivation for this project was two-fold: 
* Building a fully self-hostable document management system to get my ever growing number of pdfs under control
* A playground for applying the principles taught in the book *Architecture Patterns with Python - Enabling Test-Driven Development, Domain-Driven Design, and Event-Driven Microservices*[^1]

`Note`: I paused working on this project after I found out that the [Paperless-ngx](https://github.com/paperless-ngx) project worked on a release[^2] adding RAG capabilities to their already mature document management system, which made my project basically redundant.

[^1] The book is freely accessable at: https://www.cosmicpython.com/book/preface  
[^2] They introduced AI capabilities with [Paperless-ngx v3.0.0](https://github.com/paperless-ngx/paperless-ngx/releases/tag/v3.0.0) in July 2026.

# Overview
## Backend, DB and AI/ML Services
The FastAPI powered backend which orchestrates document ingestion and storage, can be found inside the `/app` folder.

The backend is dependent on having access to endpoints of the following services:
* DB:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; PostgreSQL
* PDF Processing & OCR: &nbsp;&nbsp;Docling(-serve)
* Embeddings & LLMs: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;OpenAI compatible endpoints for which I used llama.cpp

The compose file I use for starting up these services can be found in the `/docker` folder.

## Frontend
The React/Next.js powered frontend, which is located in the `/frontend` folder, was fully vibe-coded as I dedicated most of my time to the backend and I just wanted something to look at.

# Installation Notes
In its current state I would not recommend installing this repo on your machine. If you, by any chance, stumbled into this repository because you are looking for a document management system or a local RAG engine, I would recommend you to have a look at the list of similar projects in the [Similar Projects](#similar-projects) section.

## Dependency Conflicts
`docling-serve` is installed manually with `--no-deps` because its dependency constraints conflict with `pydantic-ai` (Pydantic version resolution issues).

Install it after setting up the environment:

```bash
uv sync
uv pip install --no-deps docling-serve==1.16.1
```

# Design Decisions
## Pagewise Docling Conversion
Reasons:
* Docling has unresolved issues with large pdf files; see also: 
    * https://github.com/docling-project/docling/issues/1283
    * https://github.com/docling-project/docling/issues/1654
* Increasing Throughput: Utilizing multiple docling-serve instances - each instance with a seperate dedicated GPU - to parallelize pdf processing
## Transition to SQLAlchemy
After having started the project with raw SQL without investing much thought into this, I came to the conclusion that I certainly do want to use am ORM for schema migration. Adopting SQLAlchemy is also the last thing I was working on until I paused the project. The unfinished adoption can be found in the branch `incorporate_sqlalchemy`

# Miscellanious
## Similar projects
I like to keep track of what is happening in this rapidly moving space, so that I don´t reinvent the wheel. Here is an unordered list of relevant projects I´ve been following:

https://github.com/open-webui/open-webui  
https://github.com/paperless-ngx/paperless-ngx  
https://github.com/ggozad/haiku.rag  
https://github.com/duckling-ui/duckling/tree/main  
https://github.com/Mintplex-Labs/anything-llm  
https://github.com/Cinnamon/kotaemon/tree/main  
https://github.com/grobidOrg/grobid  