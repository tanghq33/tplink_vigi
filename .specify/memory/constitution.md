<!--
Sync Impact Report:
Version: 0.0.0 → 1.0.0
Rationale: Initial constitution establishment with Home Assistant component principles

Principles Added:
  - I. Type Safety & Static Analysis
  - II. Defensive Error Handling
  - III. User Experience Consistency
  - IV. Performance & Resource Efficiency
  - V. Home Assistant Integration Standards

Templates Status:
  ✅ .specify/templates/plan-template.md - Constitution Check section ready
  ✅ .specify/templates/spec-template.md - Requirements alignment verified
  ✅ .specify/templates/tasks-template.md - Task categorization supports principles

Follow-up TODOs: None - all placeholders filled
-->

# TP-Link VIGI Home Assistant Integration Constitution

## Core Principles

### I. Type Safety & Static Analysis

**Principle**: All Python code MUST include explicit type annotations for functions,
methods, class attributes, and variables where type cannot be trivially inferred.
Type hints MUST be validated using mypy in strict mode.

**Requirements**:
- Every function and method signature MUST declare parameter types and return types
- Class attributes MUST be annotated with types
- Complex return types (unions, optionals, generics) MUST be explicitly declared
- Type: ignore comments are PROHIBITED unless accompanied by a detailed comment
  explaining why the type system cannot express the constraint
- mypy MUST pass with zero errors in strict mode before any code is merged

**Rationale**: Python's dynamic nature makes it prone to runtime type errors.
Explicit type annotations catch errors at development time, improve IDE support,
serve as inline documentation, and prevent entire classes of bugs before code
reaches production. Home Assistant components handle user data and device state;
type safety prevents data corruption and unexpected failures.

### II. Defensive Error Handling

**Principle**: All code MUST handle errors defensively with comprehensive logging
and graceful degradation. Edge cases MUST be anticipated and handled explicitly.

**Requirements**:
- Every external API call, file operation, or network request MUST be wrapped in
  appropriate exception handling
- Exceptions MUST be caught at the appropriate level (component vs entity level)
- Error messages MUST be logged with sufficient context for debugging:
  - Use _LOGGER.error() for unexpected failures that affect functionality
  - Use _LOGGER.warning() for edge cases that are handled but unexpected
  - Use _LOGGER.debug() for expected operational information
- Error logs MUST include: operation attempted, relevant identifiers (device ID,
  entity ID), exception type and message, sanitized context data
- NEVER allow exceptions to bubble up and crash Home Assistant
- Provide fallback values or disable entities gracefully when errors occur
- Input validation MUST check for None, empty strings, out-of-range values, and
  invalid formats BEFORE using data

**Edge Case Requirements**:
- Handle network timeouts and connection failures
- Handle malformed API responses and missing expected fields
- Handle device offline/unavailable states
- Handle concurrent access and race conditions
- Handle configuration changes during runtime
- Handle Home Assistant restarts and state recovery

**Rationale**: Home Assistant runs 24/7 in production environments. A single
unhandled exception can crash the entire integration or even affect other
integrations. Defensive coding with comprehensive logging enables users and
maintainers to diagnose issues quickly. Edge cases are inevitable in real-world
deployments; anticipating and handling them prevents support burden and improves
reliability.

### III. User Experience Consistency

**Principle**: The integration MUST follow Home Assistant UX conventions and provide
predictable, consistent behavior that matches user expectations from other
integrations.

**Requirements**:
- Entity naming MUST follow Home Assistant conventions: "[Device Name] [Entity Type]"
- Entity unique IDs MUST be stable across restarts and configuration changes
- Configuration flow MUST use Home Assistant's config flow pattern with proper
  validation and helpful error messages
- Options flow MUST be provided for runtime reconfiguration
- Entity icons MUST use Material Design Icons (mdi:) that match entity purpose
- Device class MUST be set appropriately for each entity type
- Entity availability MUST be tracked and reported accurately
- State attributes MUST follow Home Assistant naming conventions (snake_case)
- Documentation strings MUST explain purpose and behavior clearly

**Rationale**: Consistency reduces cognitive load for users and makes the
integration feel native to Home Assistant. Users expect certain patterns and
behaviors; deviating creates confusion and support burden. Following conventions
ensures compatibility with Home Assistant features like energy monitoring,
automations, and UI card generation.

### IV. Performance & Resource Efficiency

**Principle**: The integration MUST minimize resource usage and avoid blocking
operations that degrade Home Assistant performance.

**Requirements**:
- All I/O operations (API calls, file access) MUST be async using asyncio
- Polling intervals MUST be configurable and default to reasonable values (≥30s)
- API requests MUST be batched when possible to minimize network overhead
- Avoid holding references to large data structures unnecessarily
- Use Home Assistant's DataUpdateCoordinator for centralized polling
- Cache data appropriately to avoid redundant API calls
- Set appropriate timeouts for all network operations (default: 10s)
- Cleanup resources properly in async_unload_entry (close connections, cancel tasks)

**Performance Targets**:
- Entity state updates MUST complete in <1 second (p95)
- Configuration flow steps MUST respond in <2 seconds (p95)
- Memory usage MUST remain stable over 24+ hour operation (no leaks)
- Integration MUST NOT block Home Assistant's event loop for >50ms

**Rationale**: Home Assistant often runs on resource-constrained hardware (Raspberry
Pi). Blocking operations freeze the UI and delay automations. Async operations
ensure responsiveness. Excessive polling wastes CPU, network bandwidth, and device
battery. Efficient resource usage ensures Home Assistant remains responsive even
with many integrations installed.

### V. Home Assistant Integration Standards

**Principle**: The integration MUST comply with Home Assistant's quality scale
requirements and architectural patterns.

**Requirements**:
- Integration MUST have a manifest.json with correct metadata
- Integration MUST use config entries (no YAML configuration)
- Integration MUST implement async_setup, async_setup_entry, async_unload_entry
- Entities MUST inherit from appropriate base classes (BinarySensorEntity, etc.)
- Integration MUST provide translations (strings.json, en.json)
- Integration MUST handle Home Assistant shutdown gracefully
- Device info MUST be provided for all entities to enable device grouping
- Integration MUST respect Home Assistant's disabled entity pattern
- Services (if any) MUST be registered with proper schemas
- Integration MUST pass Home Assistant's hassfest validation

**Testing Requirements**:
- Unit tests MUST cover core business logic
- Integration tests MUST verify entity lifecycle (setup, update, unload)
- Mock external dependencies in tests (no real API calls)
- Test coverage MUST be ≥80% for core integration files

**Rationale**: Home Assistant has established patterns that ensure reliability,
maintainability, and compatibility. Following these patterns makes the integration
eligible for inclusion in Home Assistant core and ensures long-term supportability.
Quality scale compliance signals maturity and reliability to users.

## Code Quality Standards

### Documentation

- Every module MUST have a docstring explaining its purpose
- Public functions and methods MUST have docstrings with:
  - Brief description of purpose
  - Args section describing each parameter with type
  - Returns section describing return value with type
  - Raises section documenting expected exceptions
- Use Google-style docstrings for consistency
- Complex logic MUST be commented inline to explain "why", not "what"

### Code Organization

- One entity class per file for clarity
- Group related functionality into modules (config_flow, const, coordinator, etc.)
- Follow Home Assistant's recommended directory structure:
  ```
  custom_components/tplink_vigi/
  ├── __init__.py           # Integration setup
  ├── binary_sensor.py      # Binary sensor entities
  ├── config_flow.py        # Configuration UI
  ├── const.py              # Constants
  ├── coordinator.py        # Data update coordinator
  ├── manifest.json         # Integration metadata
  ├── strings.json          # UI strings
  └── translations/
      └── en.json           # English translations
  ```
- Avoid circular imports by using TYPE_CHECKING guards
- Keep functions focused and single-purpose (≤50 lines preferred)

### Dependencies

- Minimize external dependencies (requirements in manifest.json)
- Pin dependency versions for reproducibility
- Prefer Home Assistant's built-in HTTP client (aiohttp) over external clients
- Document why each dependency is needed

## Governance

### Amendment Process

1. Proposed amendments MUST be documented in a PR description
2. Amendments MUST include rationale for the change
3. MINOR version bumps require review of impact on active features
4. MAJOR version bumps require migration plan for existing code
5. All amendments MUST update the Sync Impact Report

### Version Policy

- Version format: MAJOR.MINOR.PATCH (semantic versioning)
- MAJOR: Principle removal, redefinition, or backward-incompatible changes
- MINOR: New principle added, principle materially expanded
- PATCH: Clarifications, wording improvements, typo fixes

### Compliance

- Every PR MUST verify compliance with all principles during code review
- Constitution takes precedence over ad-hoc decisions or convenience
- Complexity and principle violations MUST be explicitly justified in plan.md
- Quarterly constitution review to ensure principles remain relevant

### Enforcement

- Pre-commit hooks SHOULD run mypy, black, isort, and pylint
- CI pipeline MUST enforce type checking and linting
- Code review MUST verify defensive error handling and logging
- Integration tests MUST verify Home Assistant compatibility

**Version**: 1.0.0 | **Ratified**: 2025-11-20 | **Last Amended**: 2025-11-20
