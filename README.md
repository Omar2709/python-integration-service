# Python Integration Service

Backend service built with Python and FastAPI to practice and demonstrate production-oriented integration patterns for third-party APIs.

The project focuses on designing integrations that are explicit, testable, maintainable, and resilient. It is being developed incrementally as part of a backend engineering training plan.

## Goals

The main goals of this project are to practice and demonstrate:

* Clean Python design and object-oriented programming.
* Dependency inversion and transport abstractions.
* Custom exception hierarchies for external integrations.
* Configurable retry mechanisms.
* Iterators, generators, and lazy pagination.
* Context managers and deterministic resource cleanup.
* REST API integrations.
* HTTP transport with HTTPX.
* Authentication and secure configuration using environment variables.
* HTTP error translation and transient failure classification.
* Rate-limit handling.
* Data validation and transformation.
* Testing with `pytest`.
* Mocks, fixtures, and coverage.
* Resilience patterns such as backoff, jitter, timeouts, and rate-limit handling.
* Continuous integration with GitHub Actions.
* Docker and continuous deployment.
* Cloud-oriented integration architecture.
* Basic Kubernetes deployment concepts.
* Security concepts relevant to backend integrations.

## Tech Stack

* Python 3.13+
* FastAPI
* HTTPX
* Pydantic Settings
* Uvicorn
* pytest
* pytest-cov
* Ruff
* uv
* GitHub Actions

## Project Structure

```text
python-integration-service/
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── python_integration_service/
│       ├── __init__.py
│       ├── main.py
│       └── integrations/
│           ├── __init__.py
│           ├── exceptions.py
│           ├── httpx_transport.py
│           ├── managed_resource.py
│           ├── page_iterator.py
│           ├── pagination.py
│           ├── resource_context.py
│           ├── retry.py
│           ├── transport.py
│           └── vendor_client.py
├── tests/
│   └── integrations/
│       ├── test_httpx_transport.py
│       ├── test_managed_resource.py
│       ├── test_page_iterator.py
│       ├── test_pagination.py
│       ├── test_resource_context.py
│       └── test_retry.py
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

Generated local directories and files such as `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.coverage`, `coverage.xml`, and `junit.xml` are intentionally omitted from the project structure.

Local editor configuration such as `.vscode/` is also intentionally kept outside the repository.

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

* `IntegrationError`
* `ConfigurationError`
* `AuthenticationError`
* `RateLimitError`
* `TransientIntegrationError`

This allows higher-level application code to distinguish integration-specific failures from unrelated programming errors.

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
    +-- HttpxTransport
```

This follows the Dependency Inversion Principle and makes the integration client easier to test while allowing the concrete HTTP implementation to be replaced independently.

### HTTPX transport

The project includes a concrete HTTP transport implemented with `httpx.Client`.

`HttpxTransport` is responsible for performing outbound HTTP requests while keeping HTTP-specific behavior behind the `Transport` abstraction.

Current behavior includes:

* Outbound requests through `httpx.Client`.
* Bearer authentication headers.
* Configurable request timeouts.
* Translation of HTTP failures into integration-specific exceptions.
* Translation of HTTPX timeout errors into transient integration failures.
* Translation of network and connection errors into transient integration failures.
* HTTP `401` handling as an authentication failure.
* HTTP `429` handling as a rate-limit failure.
* `Retry-After` handling for rate-limited responses.
* Classification of HTTP `500`, `502`, `503`, and `504` responses as transient integration failures.

This keeps HTTP-specific concerns isolated from higher-level application logic.

### Vendor client

`VendorClient` currently provides:

* Base URL configuration.
* Access-token configuration.
* Timeout validation.
* Environment-based construction with `from_env`.
* URL construction.
* URL validation.
* Delegation of outbound requests to a `Transport`.

Secrets such as access tokens are expected to come from environment variables and must not be hardcoded or logged.

### Authentication

Outbound vendor requests support Bearer token authentication.

Conceptually:

```http
Authorization: Bearer <access-token>
```

The access token is provided through configuration and is expected to come from environment variables rather than source code.

Authentication failures returned as HTTP `401` responses are translated into `AuthenticationError`.

### HTTP error translation

The HTTP transport translates low-level HTTP and network failures into the project's integration exception hierarchy.

Current mappings include:

```text
401
  -> AuthenticationError

429
  -> RateLimitError

500 / 502 / 503 / 504
  -> TransientIntegrationError

HTTPX timeout
  -> TransientIntegrationError

HTTPX network / connection failure
  -> TransientIntegrationError
```

This prevents HTTPX-specific failures from leaking into higher-level application code and provides consistent error semantics across integrations.

### Rate-limit handling

HTTP `429 Too Many Requests` responses are recognized as rate-limit failures.

When the remote service provides a `Retry-After` header, the transport preserves the relevant rate-limit information through the integration error boundary so retry behavior can make informed decisions.

More advanced retry scheduling, exponential backoff, and jitter remain part of a later resilience phase.

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

* Validates that `max_attempts` is greater than zero.
* Retries only explicitly configured exception types.
* Immediately propagates non-retryable exceptions.
* Re-raises the final retryable exception after attempts are exhausted.
* Preserves function metadata using `functools.wraps`.

Backoff, jitter, and more advanced retry scheduling are intentionally deferred to a later resilience phase.

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

* Current page state.
* Current item position.
* Empty-page handling.
* `StopIteration`.

### Context managers

The project includes examples of both class-based and generator-based context managers.

`ManagedResource` demonstrates the context manager protocol through:

* `__enter__`
* `__exit__`
* Resource setup and cleanup.
* Cleanup even when exceptions occur.
* Explicit exception propagation.

`managed_resource` demonstrates the same lifecycle using `contextlib.contextmanager` and `try/finally`.

This illustrates how context managers provide deterministic resource cleanup for files, HTTP clients, database connections, locks, and similar resources.

## Tests

The current test suite covers:

* Retry success on the first attempt.
* Retry after transient failures.
* Immediate propagation of non-retryable exceptions.
* Exhausted retry attempts.
* Invalid retry configuration.
* Preservation of decorated function metadata.
* Generator behavior across multiple pages.
* Empty pagination scenarios.
* Manual iterator behavior.
* Iterator exhaustion with `StopIteration`.
* Iterator identity.
* Class-based context manager lifecycle.
* Cleanup after normal context exit.
* Cleanup when exceptions occur.
* Exception propagation from context managers.
* Generator-based context managers with `contextlib.contextmanager`.
* HTTP transport request behavior.
* Bearer authentication headers.
* HTTPX `MockTransport` based integration tests.
* Authentication error translation for HTTP `401`.
* Rate-limit error translation for HTTP `429`.
* `Retry-After` handling.
* Transient error classification for HTTP `500`.
* Transient error classification for HTTP `502`.
* Transient error classification for HTTP `503`.
* Transient error classification for HTTP `504`.
* Timeout error translation.
* Network and connection error translation.

Current test count:

```text
35 tests
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

Check formatting without modifying files:

```bash
uv run ruff format --check .
```

Run tests:

```bash
uv run pytest -v
```

Run tests with coverage:

```bash
uv run pytest --cov=python_integration_service --cov-report=term-missing
```

## Continuous Integration

GitHub Actions runs the project's quality checks automatically on:

* Pushes to `main`.
* Pull requests targeting `main`.
* Manual workflow executions.

The CI pipeline:

* Sets up the project Python version.
* Installs `uv`.
* Installs dependencies from the committed lockfile.
* Verifies formatting with Ruff.
* Runs Ruff lint checks.
* Executes the pytest suite.
* Generates code coverage reports.
* Generates JUnit XML test reports.
* Uploads test reports as GitHub Actions artifacts.

Conceptually:

```text
Push / Pull Request / Manual Run
              |
              v
        GitHub Actions
              |
      +-------+-------+
      |       |       |
      v       v       v
   Format    Lint    Tests
    Ruff     Ruff    pytest
                      |
                      +--> Coverage report
                      |
                      +--> JUnit report
                      |
                      +--> GitHub Actions artifacts
```

Generated reports such as `.coverage`, `coverage.xml`, and `junit.xml` are build artifacts and are not intended to be committed to the repository.

Continuous integration verifies changes automatically. Continuous deployment is intentionally not implemented yet because the project does not currently define a deployment target.

## Installation

### Requirements

* Python 3.13 or newer
* `uv`

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

* Prefer composition over unnecessary inheritance.
* Depend on abstractions at integration boundaries.
* Keep responsibilities small and explicit.
* Keep HTTP-specific behavior behind transport abstractions.
* Translate external-library failures into domain-specific integration errors.
* Retry only failures that are actually retryable.
* Never silently swallow exceptions.
* Preserve original exceptions and tracebacks when possible.
* Avoid hardcoding credentials.
* Never log access tokens or other secrets.
* Validate configuration early.
* Prefer lazy processing when large datasets do not need to be fully loaded into memory.
* Use context managers for deterministic cleanup of managed resources.
* Write tests around observable behavior rather than implementation details.
* Use HTTPX `MockTransport` to test HTTP behavior without real network calls.
* Automate repeatable quality checks through continuous integration.
* Keep integrations replaceable and easy to isolate in tests.

## Roadmap

The project will evolve incrementally.

### Completed

* [x] Initial FastAPI application.
* [x] Integration exception hierarchy.
* [x] Transport abstraction.
* [x] Vendor client foundation.
* [x] Environment-based client configuration.
* [x] Configurable retry decorator.
* [x] Retry behavior tests.
* [x] Generator fundamentals.
* [x] Manual iterator implementation.
* [x] Pagination and iterator tests.
* [x] Context manager protocol with `__enter__` and `__exit__`.
* [x] Generator-based context managers with `contextlib.contextmanager`.
* [x] HTTP transport with HTTPX.
* [x] Bearer authentication headers.
* [x] HTTP exception translation.
* [x] HTTP timeout and network error translation.
* [x] Rate-limit handling with `Retry-After`.
* [x] Transient error classification for `500`, `502`, `503`, and `504`.
* [x] `MockTransport`-based HTTP tests.
* [x] GitHub Actions continuous integration.
* [x] Automated Ruff format verification.
* [x] Automated Ruff lint checks.
* [x] Automated pytest execution.
* [x] Coverage and JUnit report generation in CI.

### Next

* [ ] Apply lazy iteration to a real paginated client flow.
* [ ] Data transformation and validation.
* [ ] Advanced pytest fixtures and mocks.
* [ ] Retry backoff and jitter.
* [ ] Client-side rate limiting.
* [ ] GraphQL integration.
* [ ] gRPC integration.
* [ ] Docker.
* [ ] Continuous deployment.
* [ ] AWS-oriented integration architecture.
* [ ] Kubernetes fundamentals.
* [ ] Security and dependency-vulnerability practices.

## Status

This repository is under active development and is intentionally built in small, reviewable increments.

Each phase adds a focused backend concept together with tests before moving to the next topic.

The current implementation includes a concrete HTTPX transport layer with authentication, HTTP error translation, timeout and network failure handling, rate-limit awareness, isolated HTTP tests without real network access, and a GitHub Actions CI pipeline that automatically verifies formatting, linting, tests, coverage, and test reports.
