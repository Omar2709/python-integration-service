# Python Integration Service

Backend service built with Python and FastAPI to practice and demonstrate production-oriented integration patterns for third-party APIs.

The project focuses on designing integrations that are explicit, testable, maintainable, and resilient. It is being developed incrementally as part of a backend engineering training plan.

## Goals**

The main goals of this project are to practice and demonstrate:

- Clean Python design and object-oriented programming.

- Dependency inversion and transport abstractions.

- Custom exception hierarchies for external integrations.

- Explicit configuration ownership.

- Composition roots and dependency wiring.

- FastAPI application lifecycle management.

- FastAPI dependency injection.

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

- Mocks, fixtures, parametrization, dependency overrides, and coverage.

- Resilience patterns such as backoff, jitter, timeouts, and rate-limit handling.

- Continuous integration with GitHub Actions.

- Docker and continuous deployment.

- Cloud-oriented integration architecture.

- Basic Kubernetes deployment concepts.

- Security concepts relevant to backend integrations.

## Tech Stack**

- Python 3.13+

- FastAPI

- HTTPX — runtime outbound HTTP transport
- httpx2 — development/testing dependency used by FastAPI / Starlette `TestClient`

- Pydantic

- Pydantic Settings

- Uvicorn

- pytest

- pytest-cov

- Ruff

- uv

- GitHub Actions

## Project Structure**

```text

python-integration-service/

├── .github/

│   └── workflows/

│       └── ci.yml

├── src/

│   └── python_integration_service/

│       ├── __init__.py

│       ├── api/

│       │   ├── __init__.py

│       │   └── vendor.py

│       ├── composition.py

│       ├── config.py

│       ├── dependencies.py

│       ├── main.py

│       └── integrations/

│           ├── __init__.py

│           ├── exceptions.py

│           ├── httpx_transport.py

│           ├── managed_resource.py

│           ├── page_iterator.py

│           ├── pagination.py

│           ├── resource_context.py

│           ├── retry.py

│           ├── transport.py

│           └── vendor_client.py

├── tests/

│   ├── api/

│   │   └── test_vendor.py

│   ├── integrations/

│   │   ├── test_httpx_transport.py

│   │   ├── test_managed_resource.py

│   │   ├── test_page_iterator.py

│   │   ├── test_pagination.py

│   │   ├── test_resource_context.py

│   │   └── test_retry.py

│   ├── test_composition.py

│   ├── test_config.py

│   ├── test_dependencies.py

│   └── test_main.py

├── .env.example

├── .gitignore

├── .python-version

├── pyproject.toml

├── uv.lock

└── README.md

```

Generated local directories and files such as `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`, `.coverage`, `coverage.xml`, and `junit.xml` are intentionally omitted from the project structure.

Local editor configuration such as `.vscode/` is also intentionally kept outside the repository.

## Current Implementation**

### FastAPI application**

The project exposes a FastAPI application with a health-check endpoint and a vendor integration endpoint.

```text

GET /health

GET /vendor/items

```

`GET /health` provides a simple way to verify that the application is running.

`GET /vendor/items` resolves the long-lived `VendorClient` through FastAPI dependency injection and delegates the provider request to `VendorClient.get("/items")`.

### Integration exception hierarchy**

Custom exceptions provide a clear domain boundary for integration failures.

Current exception types include:

- `IntegrationError`

- `ConfigurationError`

- `AuthenticationError`

- `RateLimitError`

- `TransientIntegrationError`

This allows higher-level application code to distinguish integration-specific failures from unrelated programming errors.

HTTP API mapping for these integration exceptions is intentionally deferred to the next project phase.

### Transport abstraction**

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

### Configuration**

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

`load_settings()` centralizes environment-driven construction of `Settings` and keeps the static-type suppression required by Pylance localized to the configuration boundary.

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

### Composition root**

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

The composition root exposes `create_vendor_client()` as a context manager.

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

### FastAPI application lifecycle**

The FastAPI application uses the lifespan mechanism to initialize and clean up long-lived integration resources.

During startup:

- Application settings are loaded and validated.

- The composition root creates the HTTP transport and `VendorClient`.

- The long-lived `VendorClient` is stored in `app.state`.

During shutdown:

- The integration context is exited.

- `HttpxTransport.__exit__()` performs deterministic cleanup.

- The underlying `httpx.Client` is closed.

Configuration and dependency initialization follow fail-fast semantics: if required configuration is invalid or a required dependency cannot be initialized, application startup is aborted before the service accepts traffic.

Conceptually:

```text

Uvicorn / FastAPI startup

        |

        v

load_settings()

        |

        v

create_vendor_client(settings)

        |

        v

app.state.vendor_client

        |

        v

yield -> application ready

        |

        v

shutdown

        |

        v

exit integration context

        |

        v

close httpx.Client

```

### FastAPI dependency injection**

`get_vendor_client()` provides typed access to the long-lived `VendorClient` stored in application state.

Endpoints consume the integration client through FastAPI's dependency injection system rather than reading `app.state` directly.

This keeps route handlers decoupled from application lifecycle and resource-storage details.

Conceptually:

```text

app.state.vendor_client

        |

        v

get_vendor_client(request)

        |

        v

Depends(get_vendor_client)

        |

        v

endpoint

```

The accessor uses `typing.cast()` only to communicate the expected type to static type checkers. `cast()` does not perform runtime validation or create a new object; the same application-scoped `VendorClient` instance is returned.

### Vendor API**

The project currently exposes:

```text

GET /vendor/items

```

The route is defined in `api/vendor.py` using `APIRouter` and is registered from `main.py`.

The endpoint obtains `VendorClient` through dependency injection and delegates the provider request to:

```python

vendor_client.get("/items")

```

Because the current integration stack uses synchronous `httpx.Client`, the route is implemented as a synchronous `def` endpoint. FastAPI can therefore execute the blocking route in its thread pool instead of running synchronous network I/O directly on the main event loop.

The current request flow is:

```text

GET /vendor/items

        |

        v

FastAPI router

        |

        v

Depends(get_vendor_client)

        |

        v

VendorClient.get("/items")

        |

        v

HttpxTransport.get(...)

        |

        v

httpx.Client.get(...)

```

### HTTPX transport**

The project includes a concrete HTTP transport implemented with `httpx.Client`.

`HttpxTransport` is responsible for performing outbound HTTP requests while keeping HTTP-specific behavior behind the `Transport` abstraction.

Current behavior includes:

- Outbound requests through `httpx.Client`.

- Bearer authentication headers.

- Configurable request timeouts.

- Context-manager support.

- Deterministic cleanup of the underlying `httpx.Client`.

- Translation of HTTP failures into integration-specific exceptions.

- Translation of HTTPX timeout errors into transient integration failures.

- Translation of network and connection errors into transient integration failures.

- HTTP `401` handling as an authentication failure.

- HTTP `429` handling as a rate-limit failure.

- `Retry-After` handling for rate-limited responses.

- Classification of HTTP `500`, `502`, `503`, and `504` responses as transient integration failures.

This keeps HTTP-specific concerns isolated from higher-level application logic.

### Vendor client**

`VendorClient` is responsible for provider-specific request composition while depending only on the `Transport` abstraction.

Current responsibilities include:

- Base URL ownership.

- URL construction.

- Delegation of outbound requests to a `Transport`.

HTTP authentication, timeout configuration, environment-variable loading, configuration parsing, and transport lifecycle management are intentionally kept outside `VendorClient`.

Conceptually:

```text

VendorClient

├── base_url

├── build_url()

└── Transport

```

This keeps the client focused on provider-specific behavior rather than infrastructure configuration.

### Authentication**

Outbound vendor requests support Bearer token authentication.

Conceptually:

```http

Authorization: Bearer <access-token>

```

The access token is loaded through `Settings`, represented as `SecretStr`, explicitly extracted in the composition root, and passed to `HttpxTransport`.

Real credentials must not be hardcoded or logged.

Authentication failures returned as HTTP `401` responses are translated into `AuthenticationError`.

### HTTP error translation**

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

Other non-success HTTP statuses are translated into `IntegrationError`.

This prevents HTTPX-specific failures from leaking into higher-level application code and provides consistent error semantics across integrations.

### Rate-limit handling**

HTTP `429 Too Many Requests` responses are recognized as rate-limit failures.

When the remote service provides a `Retry-After` header, the transport preserves the relevant rate-limit information through the integration error boundary so retry behavior can make informed decisions.

More advanced retry scheduling, exponential backoff, and jitter remain part of a later resilience phase.

### Retry decorator**

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

### Generators and lazy iteration**

`iter_items` demonstrates lazy iteration using a generator.

Instead of building one large collection in memory, values are produced progressively.

This pattern will later be applied to paginated third-party APIs.

### Manual iterator**

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

### Context managers**

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

FastAPI's lifespan mechanism now integrates that resource ownership into the application lifecycle.

These examples illustrate how context managers provide deterministic resource cleanup for files, HTTP clients, database connections, locks, and similar resources.

### Testing HTTP client dependency

The production integration transport continues to use `httpx` through `HttpxTransport`.

`httpx2` is installed only as a development dependency for the FastAPI / Starlette `TestClient` used by the test suite.

Conceptually:

```text
httpx
-> runtime dependency
-> HttpxTransport
-> outbound vendor requests

httpx2
-> development/testing dependency
-> FastAPI / Starlette TestClient
-> application and router tests
```

This separation keeps production integration concerns independent from the HTTP client used internally by the testing stack.

## Tests**

The current test suite covers:

- FastAPI lifespan startup and shutdown.
- Fail-fast application initialization.
- Typed access to application state.

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

- `Retry-After` handling.

- Transient error classification for HTTP `500`.

- Transient error classification for HTTP `502`.

- Transient error classification for HTTP `503`.

- Transient error classification for HTTP `504`.

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

- FastAPI lifespan startup.

- FastAPI lifespan shutdown and resource cleanup.

- Fail-fast startup when configuration loading fails.

- Fail-fast startup when dependency construction fails.

- Prevention of downstream dependency construction after configuration failure.

- Typed access to application state through `get_vendor_client()`.

- Object identity preservation for the application-scoped `VendorClient`.

- FastAPI dependency injection with `Depends(get_vendor_client)`.

- Vendor router behavior.

- Dependency overrides for isolated API tests.

- HTTP response behavior for `GET /vendor/items` without real network calls.

Current test count:

```text

53 tests

```

Run the suite with:

```bash

uv run pytest -v

```

## Code Quality**

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

## Continuous Integration**

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

      |       |       |

      v       v       v

   Format    Lint    Tests

    Ruff     Ruff    pytest

                      |

                      +--> Coverage report

                      |

                      +--> JUnit report

                      |

                      +--> GitHub Actions artifacts

```

Generated reports such as `.coverage`, `coverage.xml`, and `junit.xml` are build artifacts and are not intended to be committed to the repository.

Continuous integration verifies changes automatically. Continuous deployment is intentionally not implemented yet because the project does not currently define a deployment target.

## Installation**

### Requirements**

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

## Environment Variables**

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

-> required

-> valid HTTP/HTTPS URL



VENDOR_ACCESS_TOKEN

-> required

-> cannot be empty

-> cannot contain only whitespace



VENDOR_TIMEOUT

-> optional

-> defaults to 30.0

-> must be greater than 0

```

Real secrets must be provided through environment variables or a proper secret-management system.

`SecretStr` reduces accidental disclosure through string representations but does not encrypt secret values in application memory.

## Running the API**

Start the FastAPI application with Uvicorn:

```bash

uv run uvicorn python_integration_service.main:app --reload

```

Verify the health endpoint:

```text

http://127.0.0.1:8000/health

```

The expected result is a successful health response from the application.

The application also registers:

```text

GET /vendor/items

```

The vendor endpoint requires valid application configuration and a reachable vendor API. Automated tests do not require a real vendor service: they use dependency overrides and test doubles to keep API tests deterministic and network-independent.

## Development Principles**

The project follows several principles that will guide future changes:

- Prefer composition over unnecessary inheritance.

- Depend on abstractions at integration boundaries.

- Keep responsibilities small and explicit.

- Keep configuration parsing separate from dependency construction.

- Centralize concrete dependency wiring in a composition root.

- Keep application startup and shutdown responsibilities explicit through FastAPI lifespan.

- Fail fast when required configuration or dependencies cannot be initialized.

- Store long-lived application resources centrally, but expose them to endpoints through typed dependencies.

- Avoid direct `app.state` access from route handlers.

- Keep HTTP-specific behavior behind transport abstractions.

- Keep Pydantic-specific types at the configuration boundary.

- Translate external-library failures into domain-specific integration errors.

- Retry only failures that are actually retryable.

- Never silently swallow exceptions.

- Preserve original exceptions and tracebacks when possible.

- Avoid hardcoding credentials.

- Never log access tokens or other secrets.

- Validate configuration early.

- Make secret extraction explicit and localized.

- Prefer lazy processing when large datasets do not need to be fully loaded into memory.

- Use context managers for deterministic cleanup of managed resources.

- Make resource ownership and lifecycle explicit.

- Use synchronous `def` routes when the current call chain performs blocking synchronous I/O.

- Migrate to an async call chain only when the underlying integration client is async-capable.

- Write tests around observable behavior rather than implementation details.

- Patch dependencies where they are looked up by the code under test.

- Use FastAPI dependency overrides to isolate route tests from production lifecycle concerns.

- Use minimal FastAPI test applications when testing routers independently from production startup.

- Use HTTPX `MockTransport` to test HTTP behavior without real network calls.

- Use pytest fixtures and `monkeypatch` to isolate test state.

- Automate repeatable quality checks through continuous integration.

- Keep integrations replaceable and easy to isolate in tests.

## Roadmap**

The project will evolve incrementally.

### Completed**

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

- [x] FastAPI lifespan integration for long-lived dependencies.

- [x] Fail-fast application startup for invalid configuration and dependency initialization failures.

- [x] Typed `get_vendor_client()` application-state dependency.

- [x] FastAPI dependency injection with `Depends(get_vendor_client)`.

- [x] Dedicated vendor `APIRouter`.

- [x] `GET /vendor/items` endpoint.

- [x] Isolated vendor-router tests using dependency overrides.

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

- [x] FastAPI lifespan tests.

- [x] Dependency-injection tests.

- [x] GitHub Actions continuous integration.

- [x] Automated Ruff format verification.

- [x] Automated Ruff lint checks.

- [x] Automated pytest execution.

- [x] Coverage and JUnit report generation in CI.

### Next**

- [ ] Map integration exceptions to stable HTTP API responses.

- [ ] Apply lazy iteration to a real paginated client flow.

- [ ] Data transformation and validation.

- [ ] Advanced pytest fixtures and mocks.

- [ ] Retry backoff and jitter.

- [ ] Client-side rate limiting.

- [ ] Evaluate an asynchronous HTTP transport and end-to-end async request flow.

- [ ] GraphQL integration.

- [ ] gRPC integration.

- [ ] Docker.

- [ ] Continuous deployment.

- [ ] AWS-oriented integration architecture.

- [ ] Kubernetes fundamentals.

- [ ] Security and dependency-vulnerability practices.

## Status**

This repository is under active development and is intentionally built in small, reviewable increments.

Each phase adds a focused backend concept together with tests before moving to the next topic.

The current implementation includes validated application configuration with Pydantic Settings, explicit secret handling with `SecretStr`, a composition root that wires and owns integration resources, FastAPI lifespan integration with fail-fast startup and deterministic shutdown, typed dependency injection for an application-scoped `VendorClient`, a dedicated vendor router with `GET /vendor/items`, a focused `VendorClient`, a concrete synchronous HTTPX transport with authentication and deterministic cleanup, HTTP error translation, timeout and network failure handling, rate-limit awareness, isolated tests without real network access, and a GitHub Actions CI pipeline that verifies formatting, linting, tests, coverage, and test reports.

The current suite contains 53 passing tests. The FastAPI testing stack currently runs without deprecation warnings after adding `httpx2` as a development dependency for `TestClient` and updating the compatible Starlette version in the lockfile.
