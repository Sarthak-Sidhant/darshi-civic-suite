# Contributing to Darshi

Thank you for your interest in contributing to Darshi! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/darshi.git
   cd darshi
   ```

2. **Start infrastructure services**
   ```bash
   docker compose up -d
   ```

3. **Set up backend**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your values
   uvicorn app.main:app --reload --port 8080
   ```

4. **Set up frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Development Guidelines

### Code Style

**Backend (Python)**
- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Use async/await for database and external API operations
- Always raise specific exceptions, never return None/False for errors

**Frontend (TypeScript/Svelte)**
- Use TypeScript strict mode
- Use SvelteKit 5 Runes API (`$state`, `$derived`, `$effect`, `$props`)
- Always use toast notifications instead of alert()
- Use `goto()` for navigation instead of `window.location.href`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): resolve bug
refactor(scope): restructure code
docs(scope): update documentation
test(scope): add/modify tests
chore(scope): build/dependencies
```

### Pull Requests

1. Create a feature branch from `main`
2. Make your changes
3. Run tests: `pytest` (backend), `npm run test` (frontend)
4. Run type checking: `npm run check` (frontend)
5. Submit a PR with a clear description

### Testing

**Backend**
```bash
pytest                    # All tests
pytest -v                 # Verbose
pytest -k "test_name"     # Specific test
pytest --cov=app          # With coverage
```

**Frontend**
```bash
npm run test              # All tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage
```

## Architecture Overview

- **Backend**: FastAPI + PostgreSQL + Redis
- **Frontend**: SvelteKit 5 + TypeScript
- **Infrastructure**: Docker + Nginx + Cloudflare R2

See [CLAUDE.md](./CLAUDE.md) for detailed architecture documentation.

## Need Help?

- Open an issue for bugs or feature requests
- Check existing documentation in `/docs`
- Review [CLAUDE.md](./CLAUDE.md) for codebase conventions
