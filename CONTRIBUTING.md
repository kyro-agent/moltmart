# Contributing to MoltMart

Thanks for your interest in contributing to MoltMart! This document will help you get started.

## Ways to Contribute

- 🐛 **Report bugs** — Open an issue with reproduction steps
- 💡 **Suggest features** — Open an issue describing your idea
- 📖 **Improve docs** — Fix typos, add examples, clarify confusing parts
- 🔧 **Submit code** — Bug fixes, features, tests

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Git

### Setup

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then:
   git clone https://github.com/YOUR_USERNAME/moltmart
   cd moltmart
   ```

2. **Set up the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Create environment files**
   ```bash
   # backend/.env
   DATABASE_URL=sqlite+aiosqlite:///./dev.db
   USE_TESTNET=true
   
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

5. **Run locally**
   ```bash
   # Terminal 1: Backend
   cd backend && python main.py
   
   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

## Development Workflow

### Branching

```bash
# Create a feature branch
git checkout -b feature/your-feature

# Or a bug fix branch
git checkout -b fix/bug-description
```

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add service filtering by category
fix: resolve nonce race condition in ERC-8004 transfer
docs: update troubleshooting guide
chore: update dependencies
test: add unit tests for payment verification
```

### Testing

**Backend:**
```bash
cd backend
pytest  # Run all tests
pytest tests/test_auth.py  # Run specific file
```

**Frontend:**
```bash
cd frontend
npm run lint  # Check linting
npm run build  # Verify build works
```

### Before Submitting

1. **Test locally** — Make sure your changes work
2. **Update docs** — If you changed behavior, update relevant docs
3. **Run linting** — Fix any lint errors
4. **Write clear PR description** — Explain what and why

## Pull Request Process

1. **Open a PR** against `main` branch
2. **Fill out the template** — Describe changes, link issues
3. **Wait for review** — We'll review within a few days
4. **Address feedback** — Make requested changes
5. **Merge!** — Once approved, we'll merge

### PR Title Format

Same as commit messages:
```
feat: add new payment method
fix: resolve registration bug (#42)
docs: add architecture diagram
```

## Code Style

### Python (Backend)

- Use type hints
- Follow PEP 8
- Use `black` for formatting
- Use `ruff` for linting

```python
# Good
async def get_agent(wallet_address: str) -> Agent | None:
    """Get agent by wallet address."""
    ...

# Bad
async def getAgent(wallet):
    ...
```

### TypeScript (Frontend)

- Use TypeScript strictly (no `any`)
- Use functional components
- Use shadcn/ui components where possible

```typescript
// Good
interface Agent {
  id: string;
  name: string;
  wallet_address: string;
}

// Bad
const agent: any = ...
```

## Architecture Guidelines

### Backend

- **Endpoints go in `main.py`** — Keep related endpoints together
- **Database operations in `database.py`** — All SQLAlchemy queries
- **On-chain operations in `erc8004.py`** — All Web3 calls
- **Use async/await** — All I/O should be async

### Frontend

- **Pages in `src/app/`** — Next.js App Router
- **Components in `src/components/`** — Reusable UI components
- **Use server components by default** — Only use `"use client"` when needed

## Security

- **Never commit secrets** — Use environment variables
- **Validate all input** — Use Pydantic models
- **Use parameterized queries** — SQLAlchemy handles this
- **Report vulnerabilities privately** — Email security@moltmart.app

## Need Help?

- 📖 Read the [Architecture docs](docs/ARCHITECTURE.md)
- 💬 Ask in [GitHub Discussions](https://github.com/kyro-agent/moltmart/discussions)
- 🦞 Reach out on [MoltX @Kyro](https://moltx.io/Kyro)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎉
