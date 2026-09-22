# Python Integration Service

Backend service built with Python and FastAPI to practice and demonstrate production-oriented integration patterns for third-party APIs.

The project focuses on designing integrations that are explicit, testable, maintainable, and resilient. It is being developed incrementally as part of a backend engineering training plan.

## Goals

The main goals of this project are to practice and demonstrate:

- Clean Python design and object-oriented programming.
- Dependency inversion and transport abstractions.
- Custom exception hierarchies for external integrations.
- Configurable retry mechanisms.
- Iterators, generators, and lazy pagination.
- REST API integrations.
- Authentication and secure configuration using environment variables.
- Data validation and transformation.
- Testing with `pytest`.
- Mocks, fixtures, and coverage.
- Resilience patterns such as backoff, jitter, timeouts, and rate-limit handling.
- Docker and CI/CD.
- Cloud-oriented integration architecture.
- Basic Kubernetes deployment concepts.
- Security concepts relevant to backend integrations.

## Tech Stack

- Python 3.13+
- FastAPI
- HTTPX
- Pydantic Settings
- Uvicorn
- pytest
- pytest-cov
- Ruff
- uv

## Project Structure

```text
python-integration-service/
├── src/
│   └── python_integration_service/
│       ├── __init__.py
│       ├── main.py
│       └── integrations/
│           ├── __init__.py
│           ├── exceptions.py
│           ├── page_iterator.py
│           ├── pagination.py
│           ├── retry.py
│           ├── transport.py
│           └── vendor_client.py
├── tests/
│   └── integrations/
│       ├── test_page_iterator.py
│       ├── test_pagination.py
│       └── test_retry.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## Current Implementation

### FastAPI application

The project includes a minimal FastAPI application with a health-check endpoint.

```text
GET /health
```

This provides a simple way to verify that the application is running.

### Integration exception hierarchy

Custom exceptions provide a clear domain boundary for integration failures.

Current exception types include:

- `IntegrationError`
- `ConfigurationError`
- `AuthenticationError`
- `RateLimitError`
- `TransientIntegrationError`

This allows higher-level application code to distinguish integration-specific errors from unrelated programming errors.

### Transport abstraction

`Transport` defines an abstraction for outbound communication.

`VendorClient` depends on this abstraction instead of depending directly on a concrete HTTP library.

Conceptually:

```text
VendorClient
    |
    v
Transport
    |
    +-- FakeTransport
    +-- future HttpxTransport
```

This follows the Dependency Inversion Principle and makes the integration client easier to test.

### Vendor client

`VendorClient` currently provides:

- Base URL configuration.
- Access-token configuration.
- Timeout validation.
- Environment-based construction with `from_env`.
- URL construction.
- URL validation.
- Delegation of outbound requests to a `Transport`.

Secrets such as access tokens are expected to come from environment variables and must not be hardcoded or logged.

### Retry decorator

The project includes a configurable `retry` decorator.

Example:

```python
@retry(
    max_attempts=3,
    retry_on=(TimeoutError, ConnectionError),
)
def call_vendor(): ...
```

Current behavior:

- Validates that `max_attempts` is greater than zero.
- Retries only explicitly configured exception types.
- Immediately propagates non-retryable exceptions.
- Re-raises the final retryable exception after attempts are exhausted.
- Preserves function metadata using `functools.wraps`.

Backoff, jitter, logging, and `Retry-After` support are intentionally deferred to a later resilience phase.

### Generators and lazy iteration

`iter_items` demonstrates lazy iteration using a generator.

Instead of building one large collection in memory, values are produced progressively.

This pattern will later be applied to paginated third-party APIs.

### Manual iterator

`PageIterator` implements the iterator protocol explicitly through:

```python
__iter__()
__next__()
```

It demonstrates the mechanics that Python generators normally manage automatically:

- Current page state.
- Current item position.
- Empty-page handling.
- `StopIteration`.

## Tests

The current test suite covers:

- Retry success on the first attempt.
- Retry after transient failures.
- Immediate propagation of non-retryable exceptions.
- Exhausted retry attempts.
- Invalid retry configuration.
- Preservation of decorated function metadata.
- Generator behavior across multiple pages.
- Empty pagination scenarios.
- Manual iterator behavior.
- Iterator exhaustion with `StopIteration`.
- Iterator identity.

Current test count:

```text
15 tests
```

Run the suite with:

```bash
uv run pytest -v
```

## Code Quality

Format the project:

```bash
uv run ruff format .
```

Run lint checks:

```bash
uv run ruff check .
```

Run tests:

```bash
uv run pytest -v
```

Run tests with coverage:

```bash
uv run pytest --cov=python_integration_service --cov-report=term-missing
```

## Installation

### Requirements

- Python 3.13 or newer
- `uv`

Clone the repository:

```bash
git clone https://github.com/Omar2709/python-integration-service.git
cd python-integration-service
```

Install dependencies:

```bash
uv sync
```

## Environment Variables

Do not commit real credentials.

Create a local `.env` file based on `.env.example`.

Example variables:

```env
VENDOR_BASE_URL=https://api.example.com
VENDOR_ACCESS_TOKEN=replace-with-local-development-value
VENDOR_TIMEOUT=30
```

Real secrets must be provided through environment variables or a proper secret-management system.

## Running the API

Start the FastAPI application with Uvicorn:

```bash
uv run uvicorn python_integration_service.main:app --reload
```

Then verify the health endpoint:

```text
http://127.0.0.1:8000/health
```

The expected result is a successful health response from the application.

## Development Principles

The project follows several principles that will guide future changes:

- Prefer composition over unnecessary inheritance.
- Depend on abstractions at integration boundaries.
- Keep responsibilities small and explicit.
- Retry only failures that are actually retryable.
- Never silently swallow exceptions.
- Preserve original exceptions and tracebacks when possible.
- Avoid hardcoding credentials.
- Validate configuration early.
- Prefer lazy processing when large datasets do not need to be fully loaded into memory.
- Write tests around observable behavior rather than implementation details.
- Keep integrations replaceable and easy to isolate in tests.

## Roadmap

The project will evolve incrementally.

### Completed

- [x] Initial FastAPI application.
- [x] Integration exception hierarchy.
- [x] Transport abstraction.
- [x] Vendor client foundation.
- [x] Environment-based client configuration.
- [x] Configurable retry decorator.
- [x] Retry behavior tests.
- [x] Generator fundamentals.
- [x] Manual iterator implementation.
- [x] Pagination and iterator tests.

### Next

- [ ] Apply lazy iteration to a real paginated client flow.
- [ ] Context managers.
- [ ] Concrete HTTPX transport.
- [ ] REST integration behavior.
- [ ] Authentication flows.
- [ ] Data transformation and validation.
- [ ] Advanced pytest fixtures and mocks.
- [ ] Coverage reporting.
- [ ] Retry backoff and jitter.
- [ ] HTTP `429` and `Retry-After`.
- [ ] Rate limiting.
- [ ] GraphQL integration.
- [ ] gRPC integration.
- [ ] Docker.
- [ ] CI/CD.
- [ ] AWS-oriented integration architecture.
- [ ] Kubernetes fundamentals.
- [ ] Security and dependency-vulnerability practices.

## Status

This repository is under active development and is intentionally built in small, reviewable increments.

Each phase adds a focused backend concept together with tests before moving to the next topic.
