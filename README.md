# Python Integration Service

Backend service built with Python and FastAPI to practice and demonstrate production-oriented integration patterns for third-party APIs.

The project focuses on designing integrations that are explicit, testable, maintainable, and resilient. It is being developed incrementally as part of a backend engineering training plan.

## Goals

The main goals of this project are to practice and demonstrate:

- Clean Python design and object-oriented programming.
- Dependency inversion and transport abstractions.
- Custom exception hierarchies for external integrations.
- Explicit configuration ownership.
- Composition roots and dependency wiring.
- Configurable retry mechanisms.
- Iterators, generators, and lazy pagination.
- Context managers and deterministic resource cleanup.
- REST API integrations.
- HTTP transport with HTTPX.
- Authentication and secure configuration using environment variables.
- HTTP error translation and transient failure classification.
- Rate-limit handling.
- Data validation and transformation.
- Testing with `pytest`.
- Mocks, fixtures, parametrization, and coverage.
- Resilience patterns such as backoff, jitter, timeouts, and rate-limit handling.
- Continuous integration with GitHub Actions.
- Docker and continuous deployment.
- Cloud-oriented integration architecture.
- Basic Kubernetes deployment concepts.
- Security concepts relevant to backend integrations.

## Tech Stack

- Python 3.13+
- FastAPI
- `httpx`
- `httpx2` (development/testing)
- Pydantic
- Pydantic Settings
- Uvicorn
- pytest
- pytest-cov
- Ruff
- uv
- GitHub Actions

HTTP client dependency roles:

```text
httpx  → runtime / HttpxTransport
httpx2 → development / Starlette TestClient
```

## Project Structure

```text
python-integration-service/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .vscode/
│   ├── settings.json
│   └── tasks.json
├── src/
│   └── python_integration_service/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── errors.py
│       │   ├── schemas.py
│       │   └── vendor.py
│       ├── composition.py
│       ├── config.py
│       ├── dependencies.py
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
│           ├── vendor_client.py
│           └── vendor_schemas.py
├── tests/
│   ├── api/
│   │   └── test_vendor.py
│   ├── integrations/
│   │   ├── test_httpx_transport.py
│   │   ├── test_managed_resource.py
│   │   ├── test_page_iterator.py
│   │   ├── test_pagination.py
│   │   ├── test_resource_context.py
│   │   ├── test_retry.py
│   │   └── test_vendor_client.py
│   ├── test_composition.py
│   ├── test_config.py
│   ├── test_dependencies.py
│   └── test_main.py
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
├── uv.lock
└── README.md
```

Generated local directories and files such as `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.coverage`, `coverage.xml`, and `junit.xml` are intentionally omitted from the project structure.

Project-specific VS Code configuration is versioned for reproducible development workflows. Only shared settings and tasks are committed; personal editor preferences remain excluded from the repository.

## Current Implementation

### FastAPI application

The project includes a FastAPI application with a health-check endpoint and a paginated vendor router.

```text
GET /health
GET /vendor/items?page=N
```

Current behavior includes:

- FastAPI lifespan startup and shutdown.
- Fail-fast application initialization.
- Typed access to application state.
- FastAPI dependency injection.
- Vendor router behavior.
- Public vendor pagination.
- Request-query validation.
- Dependency overrides for isolated API tests.

#### `GET /vendor/items`

`GET /vendor/items` exposes paginated vendor item retrieval through the application's injected vendor client.

The endpoint accepts a positive `page` query parameter:

```text
GET /vendor/items?page=1
```

When the query parameter is omitted, page `1` is used by default.

Invalid page values such as:

```text
?page=0
?page=-1
```

are rejected by FastAPI request validation with the standard `422 Unprocessable Content` response before any upstream I/O occurs.

The endpoint is intentionally implemented with a synchronous `def` handler because the current transport uses synchronous `httpx.Client`. This keeps the route aligned with the integration's current synchronous I/O model.

#### Application lifespan

The FastAPI lifespan owns initialization and cleanup of the vendor integration. Application startup initializes the required integration dependency and makes it available through typed application state. Initialization is fail-fast: if the required application dependencies cannot be created, startup fails instead of serving requests with a partially initialized application.

On shutdown, the lifespan exits the managed integration context so the underlying `httpx.Client` is closed deterministically.

FastAPI dependencies provide request-time access to the initialized vendor client, while dependency overrides allow API tests to replace that dependency with isolated test doubles.

### Integration exception hierarchy

Custom exceptions provide a clear domain boundary for integration failures.

Current exception types include:

- `IntegrationError`
- `ConfigurationError`
- `AuthenticationError`
- `InvalidUpstreamResponseError`
- `TransientIntegrationError`
- `RateLimitError`
- `UpstreamTimeoutError`
- `UpstreamConnectionError`
- `UpstreamServerError`
- `UpstreamUnavailableError`

Transient integration failures share a common base while preserving semantic subtypes:

```text
IntegrationError
|
+-- ConfigurationError
+-- AuthenticationError
+-- InvalidUpstreamResponseError
|
+-- TransientIntegrationError
    |
    +-- RateLimitError
    +-- UpstreamTimeoutError
    +-- UpstreamConnectionError
    +-- UpstreamServerError
    +-- UpstreamUnavailableError
```

`InvalidUpstreamResponseError` represents a provider response that was successfully received at the transport level but does not satisfy the integration contract.

It intentionally does not inherit from `TransientIntegrationError`, because an invalid provider payload is not assumed to become valid through an immediate retry.

This allows higher-level application code to distinguish integration-specific failures from unrelated programming errors while still applying common policies to transient failures.

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

### Configuration

Application configuration is loaded and validated through Pydantic Settings.

Current configuration includes:

- Vendor base URL validation using `AnyHttpUrl`.
- Access-token protection using `SecretStr`.
- Rejection of empty or whitespace-only access tokens.
- Positive timeout validation.
- A default timeout of `30.0` seconds.
- Environment-variable loading.
- Optional `.env` file loading.

Current environment variables are:

```text
VENDOR_BASE_URL
VENDOR_ACCESS_TOKEN
VENDOR_TIMEOUT
```

Configuration parsing and validation are intentionally kept separate from dependency construction.

`Settings` owns configuration-specific representations such as `AnyHttpUrl` and `SecretStr`, while integration components receive the simpler values they actually require.

Conceptually:

```text
Environment / .env
       |
       v
    Settings
       |
       v
Composition Root
```

`SecretStr` protects the access token from accidental exposure in common string representations and logs. It is not cryptographic protection for process memory.

The real token value is extracted explicitly only where it is required to construct the HTTP transport.

### Composition root

The composition root is responsible for constructing and wiring concrete integration dependencies.

Conceptually:

```text
Settings
   |
   v
HttpxTransport
   |
   v
VendorClient
```

Its current responsibilities include:

- Extracting the real access-token value from `SecretStr`.
- Converting `AnyHttpUrl` into the `str` expected by `VendorClient`.
- Constructing `HttpxTransport`.
- Constructing `VendorClient`.
- Injecting the concrete transport through the `Transport` abstraction.
- Owning the HTTP transport lifecycle through a context manager.

The composition root currently exposes `create_vendor_client()` as a context manager.

Conceptually:

```python
with create_vendor_client(settings) as client:
    result = client.get("/items")
```

The lifecycle is:

```text
create HttpxTransport
        |
        v
create VendorClient
        |
        v
yield client
        |
        v
application usage
        |
        v
exit transport context
        |
        v
close httpx.Client
```

Cleanup occurs both after normal execution and when an exception propagates from inside the context.

This prevents Pydantic, environment loading, concrete HTTP construction, and resource-lifecycle concerns from leaking into `VendorClient`.

### HTTPX transport

The project includes a concrete HTTP transport implemented with `httpx.Client`.

`HttpxTransport` is responsible for performing outbound HTTP requests while keeping HTTP-specific behavior behind the `Transport` abstraction.

Current behavior includes:

- Outbound requests through `httpx.Client`.
- Bearer authentication headers.
- Configurable request timeouts.
- Context-manager support.
- Deterministic cleanup of the underlying `httpx.Client`.
- Translation of HTTP failures into integration-specific exceptions.
- Translation of HTTPX timeout errors into `UpstreamTimeoutError`.
- Translation of HTTPX network and connection errors into `UpstreamConnectionError`.
- HTTP `401` handling as `AuthenticationError`.
- HTTP `429` handling as `RateLimitError`.
- HTTP `500` and `502` handling as `UpstreamServerError`.
- HTTP `503` handling as `UpstreamUnavailableError`.
- HTTP `504` handling as `UpstreamTimeoutError`.
- Preservation of `Retry-After` information for rate-limited responses.

This keeps HTTP-specific concerns isolated from higher-level application logic.

### Vendor client

`VendorClient` is responsible for provider-specific request composition and pagination behavior while depending only on the `Transport` abstraction.

Current responsibilities include:

- Base URL ownership.
- URL construction.
- Delegation of outbound requests to a `Transport`.
- Fetching individual vendor pages through `get_items_page()`.
- Lazy multi-page traversal through `iter_items()`.
- Validation of caller-provided page arguments.
- Translation of invalid upstream payloads into semantic integration errors.
- Pagination cycle detection.

HTTP authentication, timeout configuration, environment-variable loading, configuration parsing, and transport lifecycle management are intentionally kept outside `VendorClient`.

Conceptually:

```text
VendorClient
├── base_url
├── build_url()
├── get()
├── get_items_page()
├── iter_items()
└── Transport
```

This keeps the client focused on provider-specific behavior rather than infrastructure configuration.

### Vendor pagination

The vendor integration supports both page-level access and lazy iteration.

```python
page = vendor_client.get_items_page(page=1)

for item in vendor_client.iter_items():
    ...
```

`get_items_page()` is the lower-level pagination primitive, while `iter_items()` provides lazy traversal across pages.

The lazy iterator reuses `get_items_page()` rather than duplicating the outbound request and validation logic.

Upstream pagination payloads are validated with dedicated Pydantic models.

The upstream models are:

```text
VendorItem
ItemsPage
```

Validation policy:

- Required fields are validated strictly.
- Type coercion is disabled for consumed fields.
- Unknown additional fields are ignored for forward compatibility.
- `next_page` must be a positive integer or `None`.
- Invalid upstream payloads are translated into `InvalidUpstreamResponseError`.
- Cyclic pagination is detected before requesting an already visited page.
- Empty pages do not imply the end of pagination; `next_page` is the source of truth.
- Non-monotonic page sequences are allowed when they do not revisit an already processed page.

For example, this sequence is valid:

```text
1 → 3 → 2 → None
```

because every page identifier is valid and no page is revisited.

This sequence is rejected:

```text
1 → 3 → 2 → 3
```

because it contains a pagination cycle.

The client does not assume that page numbers must be strictly increasing unless the provider contract explicitly requires that behavior.

### Paginated vendor API

The public endpoint exposes one vendor page per request:

```text
GET /vendor/items?page=1
```

Returning one page keeps request latency, memory consumption, and upstream call count bounded.

The endpoint uses `VendorClient.get_items_page()` rather than consuming the full `iter_items()` generator.

This prevents a normal API request from loading an arbitrarily large vendor dataset into memory or making an unbounded number of upstream requests before responding.

The public API uses its own response models rather than exposing upstream provider schemas directly.

Conceptually:

```text
VendorItem / ItemsPage
        |
        v
explicit adaptation
        |
        v
ItemResponse / ItemsPageResponse
```

The upstream models represent what the provider promises to return.

The public API models represent what this service promises to its consumers.

This allows the provider contract and the public API contract to evolve independently.

For example, a future provider field rename could be handled inside the explicit adaptation layer without necessarily changing the public API contract.

### Authentication

Outbound vendor requests support Bearer token authentication.

Conceptually:

```http
Authorization: Bearer <access-token>
```

The access token is loaded through `Settings`, represented as `SecretStr`, explicitly extracted in the composition root, and passed to `HttpxTransport`.

Real credentials must not be hardcoded or logged.

Authentication failures returned as HTTP `401` responses are translated into `AuthenticationError`.

### HTTP error translation

The integration layer translates HTTPX and upstream failures into semantic integration exceptions.

Current internal mappings include:

```text
HTTPX timeout
  -> UpstreamTimeoutError

HTTPX network / connection failure
  -> UpstreamConnectionError

401 upstream
  -> AuthenticationError

429 upstream
  -> RateLimitError

500 / 502 upstream
  -> UpstreamServerError

503 upstream
  -> UpstreamUnavailableError

504 upstream
  -> UpstreamTimeoutError

Invalid upstream payload
  -> InvalidUpstreamResponseError
```

The FastAPI boundary then translates integration exceptions into the public API contract:

```text
AuthenticationError
  -> 502 Bad Gateway
  -> upstream_authentication_error

InvalidUpstreamResponseError
  -> 502 Bad Gateway
  -> upstream_invalid_response

RateLimitError
  -> 503 Service Unavailable
  -> upstream_rate_limited

UpstreamConnectionError
  -> 502 Bad Gateway
  -> upstream_connection_error

UpstreamServerError
  -> 502 Bad Gateway
  -> upstream_server_error

UpstreamUnavailableError
  -> 503 Service Unavailable
  -> upstream_unavailable

UpstreamTimeoutError
  -> 504 Gateway Timeout
  -> upstream_timeout

IntegrationError
  -> 502 Bad Gateway
  -> upstream_integration_error
```

Upstream status codes are not propagated blindly. The public response reflects the meaning of the failure from the perspective of this API's consumers.

A provider response can also fail even when its HTTP status is successful. For example, an HTTP `200` response containing an invalid pagination payload is translated into `InvalidUpstreamResponseError`.

### Public error contract

Integration failures exposed by the API use a stable error response:

```json
{
  "code": "upstream_timeout",
  "detail": "The upstream service did not respond in time."
}
```

Invalid provider responses use:

```json
{
  "code": "upstream_invalid_response",
  "detail": "The upstream service returned an invalid response."
}
```

The public error contract is modeled with Pydantic through `ErrorResponse` and documented in OpenAPI for `502`, `503`, and `504` responses.

Internal exception messages and Pydantic validation details are not returned directly to API consumers, reducing accidental information leakage.

The public error code communicates a stable failure category while implementation-specific validation details remain inside the integration boundary.

FastAPI request-validation errors remain separate from the integration-error contract.

Conceptually:

```text
Invalid consumer request
        |
        v
FastAPI RequestValidationError
        |
        v
422 standard validation response
```

while:

```text
Upstream / integration failure
        |
        v
semantic integration exception
        |
        v
ErrorResponse {code, detail}
```

The project currently keeps FastAPI's standard `422` validation response rather than introducing a custom validation-error envelope.

### Rate-limit handling

HTTP `429 Too Many Requests` responses from the upstream provider are translated into `RateLimitError`.

When an upstream rate limit provides `Retry-After`, the API validates the value before exposing it to consumers.

Supported HTTP formats are:

- Non-negative delay seconds.
- Valid HTTP dates.

Invalid values are omitted rather than corrected or propagated blindly.

An upstream rate limit is exposed as `503 Service Unavailable`, because the limit belongs to the service-to-provider interaction rather than necessarily representing a rate limit imposed on the API consumer.

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

- Validates that `max_attempts` is greater than zero.
- Retries only explicitly configured exception types.
- Immediately propagates non-retryable exceptions.
- Re-raises the final retryable exception after attempts are exhausted.
- Preserves function metadata using `functools.wraps`.

Backoff, jitter, and more advanced retry scheduling are intentionally deferred to a later resilience phase.

### Generators and lazy iteration

`VendorClient.iter_items()` applies Python generator semantics to real upstream pagination.

Instead of building one large collection in memory, vendor items are produced progressively as iteration advances.

Pages are fetched only when the consumer requests additional items.

Conceptually:

```text
next(item)
   |
   v
fetch current page if required
   |
   v
yield item
   |
   v
follow next_page only when iteration continues
```

The generator:

- Starts from page `1` by default.
- Supports an explicit positive `start_page`.
- Fetches pages lazily.
- Skips empty intermediate pages.
- Stops when `next_page` is `None`.
- Detects pagination cycles.
- Allows non-monotonic unvisited page sequences.
- Does not materialize the complete vendor dataset in memory.

Because `iter_items()` contains `yield`, calling it creates a generator object without immediately executing its body.

Execution begins when iteration starts, for example through:

```python
next(items)
```

or:

```python
for item in items:
    ...
```

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

### Context managers

The project includes examples of both class-based and generator-based context managers.

`ManagedResource` demonstrates the context manager protocol through:

- `__enter__`
- `__exit__`
- Resource setup and cleanup.
- Cleanup after normal execution.
- Cleanup when exceptions occur.
- Explicit exception propagation.

`managed_resource` demonstrates the same lifecycle using `contextlib.contextmanager` and `try/finally`.

The composition root also uses `contextlib.contextmanager` to model ownership of `HttpxTransport` and guarantee deterministic cleanup.

These examples illustrate how context managers provide deterministic resource cleanup for files, HTTP clients, database connections, locks, and similar resources.

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
- Class-based context manager lifecycle.
- Cleanup after normal context exit.
- Cleanup when exceptions occur.
- Exception propagation from context managers.
- Generator-based context managers with `contextlib.contextmanager`.
- HTTP transport request behavior.
- Bearer authentication headers.
- HTTPX `MockTransport`-based integration tests.
- Authentication error translation for HTTP `401`.
- Rate-limit error translation for HTTP `429`.
- Semantic upstream failure classification.
- Public API exception-handler mappings.
- Public error-response contract.
- Prevention of internal error-message leakage.
- Valid `Retry-After` delay-seconds propagation.
- Valid `Retry-After` HTTP-date propagation.
- Invalid `Retry-After` rejection.
- OpenAPI documentation for `502`, `503`, and `504` responses.
- Permanent HTTP error translation.
- Timeout error translation.
- Network and connection error translation.
- Settings loading from environment variables.
- Settings URL validation.
- Default timeout configuration.
- Positive timeout validation.
- Rejection of empty access tokens.
- Rejection of whitespace-only access tokens.
- Secret-value preservation through `SecretStr`.
- Composition-root dependency wiring.
- Explicit `SecretStr` to `str` adaptation.
- `AnyHttpUrl` to `str` adaptation.
- Transport lifecycle cleanup.
- Transport cleanup when exceptions propagate.
- FastAPI lifespan startup and shutdown.
- Fail-fast application initialization.
- Typed access to application state.
- FastAPI dependency injection.
- Vendor router behavior.
- Dependency overrides for isolated API tests.
- Strict upstream pagination schema validation.
- Forward-compatible handling of additional upstream fields.
- Invalid upstream payload translation.
- Lazy multi-page fetching.
- Empty intermediate pages.
- Empty final pages.
- Cyclic pagination detection.
- Non-monotonic unvisited pagination.
- Positive page metadata validation.
- Invalid direct page argument validation.
- Invalid lazy-iteration start-page validation.
- Public paginated vendor endpoint.
- Default public page selection.
- Explicit public page selection.
- Public/upstream schema separation.
- Invalid public page query validation.
- OpenAPI documentation for the paginated success response.
- Public `upstream_invalid_response` error translation.

Current test count:

```text
89 tests
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

### VS Code automation

The repository includes project-level VS Code configuration for repeatable local quality checks.

When editing Python files:

```text
Ctrl + S
→ Ruff fix actions
→ import organization
→ Ruff formatting
```

The default VS Code build task provides a repository-wide Ruff pass:

```text
Ctrl + Shift + B
→ uv run ruff check --fix .
→ uv run ruff format .
```

Ruff applies safe automatic fixes by default. Potentially unsafe fixes are not enabled globally.

The VS Code shortcuts improve the local development workflow but do not replace the final quality gate before committing changes.

Before committing a completed development block, run:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pytest -v
git diff --check
git status --short
```

Review the full working-tree diff before staging:

```bash
git diff
```

Then stage and validate the exact commit contents:

```bash
git add .
git diff --cached --check
git diff --cached
```

## Continuous Integration

GitHub Actions runs the project's quality checks automatically on:

- Pushes to `main`.
- Pull requests targeting `main`.
- Manual workflow executions.

The CI pipeline:

- Sets up the project Python version.
- Installs `uv`.
- Installs dependencies from the committed lockfile.
- Verifies formatting with Ruff.
- Runs Ruff lint checks.
- Executes the pytest suite.
- Generates code coverage reports.
- Generates JUnit XML test reports.
- Uploads test reports as GitHub Actions artifacts.

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

Configuration rules:

```text
VENDOR_BASE_URL
→ required
→ valid HTTP/HTTPS URL

VENDOR_ACCESS_TOKEN
→ required
→ cannot be empty
→ cannot contain only whitespace

VENDOR_TIMEOUT
→ optional
→ defaults to 30.0
→ must be greater than 0
```

Real secrets must be provided through environment variables or a proper secret-management system.

`SecretStr` reduces accidental disclosure through string representations but does not encrypt secret values in application memory.

## Running the API

Start the FastAPI application with Uvicorn:

```bash
uv run uvicorn python_integration_service.main:app --reload
```

Then verify the available endpoints:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/vendor/items
http://127.0.0.1:8000/vendor/items?page=1
```

`GET /health` provides the application health check.

`GET /vendor/items` returns the first vendor page by default.

`GET /vendor/items?page=N` retrieves a selected positive page through the paginated vendor integration initialized by the FastAPI lifespan.

The vendor endpoint is implemented with `def` because the current `HttpxTransport` uses synchronous `httpx.Client`.

## Development Principles

The project follows several principles that will guide future changes:

- Prefer composition over unnecessary inheritance.
- Depend on abstractions at integration boundaries.
- Keep responsibilities small and explicit.
- Keep configuration parsing separate from dependency construction.
- Centralize concrete dependency wiring in a composition root.
- Keep HTTP-specific behavior behind transport abstractions.
- Keep Pydantic-specific types at the configuration boundary.
- Use dedicated schemas to validate upstream provider contracts.
- Keep upstream provider schemas separate from public API response schemas.
- Translate external-library failures into domain-specific integration errors.
- Translate invalid upstream payloads into semantic integration errors.
- Do not propagate upstream HTTP status codes blindly across API boundaries.
- Keep internal diagnostic messages separate from public error messages.
- Retry only failures that are actually retryable.
- Never silently swallow exceptions.
- Preserve original exceptions and tracebacks when possible.
- Avoid hardcoding credentials.
- Never log access tokens or other secrets.
- Validate configuration early.
- Make secret extraction explicit and localized.
- Validate externally supplied response metadata before exposing it downstream.
- Treat provider pagination metadata as the source of truth for traversal.
- Detect pagination cycles rather than assuming page numbers are strictly increasing.
- Prefer lazy processing when large datasets do not need to be fully loaded into memory.
- Keep public API requests bounded rather than automatically materializing complete upstream datasets.
- Validate caller input before performing unnecessary I/O.
- Use context managers for deterministic cleanup of managed resources.
- Make resource ownership and lifecycle explicit.
- Write tests around observable behavior rather than implementation details.
- Use tests as executable documentation for intentional architectural behavior.
- Test both runtime behavior and published OpenAPI contracts when they are part of the API surface.
- Patch dependencies where they are looked up by the code under test.
- Use HTTPX `MockTransport` to test HTTP behavior without real network calls.
- Use pytest fixtures and `monkeypatch` to isolate test state.
- Automate repeatable quality checks through continuous integration.
- Keep integrations replaceable and easy to isolate in tests.
- Automate safe formatting and lint fixes during local development.
- Keep shared editor automation reproducible while excluding personal editor preferences.
- Run the full quality gate before committing each completed development block.

## Roadmap

The project will evolve incrementally.

### Completed

- [x] Initial FastAPI application.
- [x] Integration exception hierarchy.
- [x] Transport abstraction.
- [x] Vendor client foundation.
- [x] Separation of configuration concerns from `VendorClient`.
- [x] Pydantic Settings-based configuration.
- [x] URL validation with `AnyHttpUrl`.
- [x] Secret handling with `SecretStr`.
- [x] Timeout configuration and validation.
- [x] Composition root for integration dependency wiring.
- [x] Explicit configuration-type adaptation at the composition boundary.
- [x] Composition-root transport lifecycle management.
- [x] Configurable retry decorator.
- [x] Retry behavior tests.
- [x] Generator fundamentals.
- [x] Manual iterator implementation.
- [x] Pagination and iterator tests.
- [x] Context manager protocol with `__enter__` and `__exit__`.
- [x] Generator-based context managers with `contextlib.contextmanager`.
- [x] HTTP transport with HTTPX.
- [x] Bearer authentication headers.
- [x] HTTP exception translation.
- [x] HTTP timeout and network error translation.
- [x] Rate-limit handling with `Retry-After`.
- [x] Transient error classification for `500`, `502`, `503`, and `504`.
- [x] `MockTransport`-based HTTP tests.
- [x] Settings validation tests.
- [x] Composition-root wiring tests.
- [x] Composition-root lifecycle tests.
- [x] FastAPI lifespan startup and shutdown.
- [x] Fail-fast application initialization.
- [x] Typed access to application state.
- [x] FastAPI dependency injection.
- [x] Vendor router behavior.
- [x] Dependency overrides for isolated API tests.
- [x] Semantic upstream exception classification.
- [x] FastAPI integration error translation.
- [x] Public API error-response contract.
- [x] Safe `Retry-After` propagation.
- [x] OpenAPI integration-error documentation.
- [x] GitHub Actions continuous integration.
- [x] Automated Ruff format verification.
- [x] Automated Ruff lint checks.
- [x] Automated pytest execution.
- [x] Coverage and JUnit report generation in CI.
- [x] VS Code Ruff format and fix automation.
- [x] Repository-wide Ruff build task.
- [x] Upstream pagination schemas.
- [x] Strict vendor-response validation.
- [x] Lazy vendor pagination.
- [x] Pagination cycle protection.
- [x] Empty-page pagination handling.
- [x] Non-monotonic unvisited pagination.
- [x] Positive pagination metadata validation.
- [x] Invalid upstream-response handling.
- [x] Public `upstream_invalid_response` error translation.
- [x] Paginated public vendor endpoint.
- [x] Public page-query validation.
- [x] Separate upstream and public pagination models.
- [x] OpenAPI paginated-success documentation.

### Next

- [ ] Data transformation and validation.
- [ ] Advanced pytest fixtures and mocks.
- [ ] Retry backoff and jitter.
- [ ] Client-side rate limiting.
- [ ] GraphQL integration.
- [ ] gRPC integration.
- [ ] Docker.
- [ ] Continuous deployment.
- [ ] AWS-oriented integration architecture.
- [ ] Kubernetes fundamentals.
- [ ] Security and dependency-vulnerability practices.

## Status

This repository is under active development and is intentionally built in small, reviewable increments.

Each phase adds a focused backend concept together with tests before moving to the next topic.

The current implementation includes validated application configuration with Pydantic Settings, explicit secret handling with `SecretStr`, a composition root that wires and owns integration resources, a concrete HTTPX transport with Bearer authentication and deterministic cleanup, semantic upstream exception classification, rate-limit handling, safe `Retry-After` propagation, strict upstream pagination schemas, lazy vendor pagination, empty-page handling, cycle detection, non-monotonic pagination support, invalid upstream-response translation, separate upstream and public response models, a paginated `GET /vendor/items?page=N` API contract, FastAPI request-query validation, stable public integration error responses, OpenAPI documentation, isolated API tests through dependency overrides, and a GitHub Actions CI pipeline that verifies formatting, linting, tests, coverage, and test reports.

The current suite contains 89 passing tests.