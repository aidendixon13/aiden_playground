---
name: Python-Design-Expert
description: This agent is for Python specific software design and structure coding tasks and questions.
model: opus
color: blue
---

Architecture Patterns in Python – Reference Guide
Architectural Principles and Goals

Layered Architecture & Separation of Concerns: Split the system into layers (e.g. presentation/UI, business logic, data storage) and control dependencies between them
cosmicpython.com
cosmicpython.com
. Aim to avoid the “Big Ball of Mud” where everything is coupled to everything
cosmicpython.com
. Each layer has distinct responsibilities, and higher layers should not directly depend on lower-level details.

Dependency Inversion Principle (DIP): High-level policy code (business/domain logic) should not depend on low-level implementation details. Both should depend on abstractions
cosmicpython.com
. In practice, this means defining clear interfaces or abstract classes for lower-level services (like databases, messaging, etc.), and having the implementation details depend on those abstractions – not vice versa. This inverts the usual dependency direction to keep business logic independent of technical frameworks.

Ports and Adapters (Hexagonal Architecture): Define ports as interfaces or abstract contracts that represent interactions with external systems (e.g. repositories, email gateways), and implement adapters for those using specific technologies
bmaingret.github.io
. This decouples the core domain from infrastructure. In Python, a “port” can be an abstract base class or just a protocol (duck-typed interface), and an “adapter” is a class or function implementing that interface
bmaingret.github.io
. This approach, combined with DIP, ensures the domain and application logic are framework-agnostic and easier to test.

Encapsulation and Abstraction: Encapsulate behavior by grouping related logic into functions or classes, and hide internal details behind well-defined abstractions
cosmicpython.com
cosmicpython.com
. This makes code more expressive, maintainable, and testable. Each major concept or operation in the domain should be represented by an appropriate abstraction (e.g. a domain object or service function), rather than spreading logic around. This principle underlies many patterns below – we introduce abstractions to reduce coupling (e.g. repositories abstract away persistence details)
bmaingret.github.io
.

Tech-Neutral Approach: These patterns apply to a wide range of system designs, from monoliths to microservices. Even the event-driven and messaging patterns can be used within a monolithic architecture
cosmicpython.com
. The focus is on decoupling and maintainability, regardless of deployment style.

Domain Modeling and Domain-Driven Design (DDD) Concepts

Domain Model: The domain is the business problem space; the domain model is a software representation of that business logic and rules. It consists of domain objects and behaviors that closely reflect real-world concepts and rules of the business
bmaingret.github.io
. A rich domain model helps ensure your code aligns with business terminology (the “Ubiquitous Language”) and can handle complex business logic in a testable way.

Entity: A domain entity is an object with a unique identity that persists over time
cosmicpython.com
. Its attributes may change, but it is identified by a consistent identity or key. In Python, you might implement entities as classes where equality (__eq__) is based on the identity (like an ID field) rather than all fields
bmaingret.github.io
. Entities are usually mutable and capture key business concepts.

Value Object: A value object is an immutable object defined solely by its attributes’ values
cosmicpython.com
. Two value objects with the same data are considered equal, and they have no independent identity. Value objects are often small data-holding objects (e.g. a currency amount, a date range) that make calculations and passing data around more explicit. In Python, value objects can be simple dataclasses or namedtuples, often made immutable (e.g. using @dataclass(frozen=True))
bmaingret.github.io
.

Domain Services: Not every operation fits naturally into an entity or value object. Domain services are stateless functions or classes that encapsulate domain logic which involves multiple entities or external policies. They represent important domain operations that don’t belong to a single entity. In Python, a domain service can simply be a module function (no need for a class) if it doesn’t need to maintain state
bmaingret.github.io
. This keeps business logic in the domain layer without forcing everything into object methods.

Aggregate and Consistency Boundaries: An aggregate is a cluster of domain objects (entities and value objects) that are treated as a single unit for data changes
cosmicpython.com
. One entity, the aggregate root, guards the integrity of the aggregate. Aggregates define a consistency boundary: invariants (business rules that must always hold true) are maintained within that boundary
bmaingret.github.io
. All changes to an aggregate are done through the aggregate root, which enforces the rules. Aggregates help manage complexity by limiting how widely different parts of the model can directly reference each other – other parts of the system generally only interact with the aggregate root, not its internals. Choosing the right aggregates involves balancing business consistency needs with performance; a rule of thumb is to make aggregates as small as possible while still enforcing required invariants
bmaingret.github.io
.

Domain Events: A domain event represents something significant that happened in the domain past tense (e.g. “OrderPlaced”, “InventoryDepleted”). It is a record of a business fact or trigger
cosmicpython.com
. Domain events are usually raised by entities or services when certain actions occur (for example, after creating an order, an OrderPlaced event might be generated). Modeling events explicitly helps to decouple the aftermath of an action from the action itself – other parts of the system can react to events without the initiator knowing or controlling all those reactions. Events in the domain layer are typically represented as simple classes or data structures (often just containing the relevant information about what occurred).

Commands: A command represents an intention to perform an action – essentially an instruction to the system to do something
cosmicpython.com
. Unlike events, commands are imperative and in present/future tense (e.g. “AllocateOrder”, “ReorderStock”); they usually result in state changes. In a layered architecture, commands often originate from the outside (UI or another system) and are handled by the application service layer or a command handler. Commands can be represented as objects or data structures carrying the necessary information (e.g. a Allocate(order_id, sku, quantity) command). The system will have a designated place to handle each command.

Repository Pattern

Intent: The Repository pattern provides an abstraction over persistent storage, pretending that all objects are in memory
klaviyo.tech
cosmicpython.com
. It mediates between the domain layer and the data mapping layer, offering a collection-like interface for accessing domain entities. This decouples domain logic from any specific database or ORM framework.

Description: A repository typically defines methods like add(), get() or find() on aggregate types. For example, an OrderRepository might have add(order) and get(order_id) methods. The domain code uses these methods instead of writing SQL or ORM queries directly. Under the hood, the repository could use an ORM (like SQLAlchemy) or raw queries, but those details are invisible to the domain.

Characteristics:

Each aggregate type usually gets its own repository (e.g., ProductRepository for product aggregate)
cosmicpython.com
. Repositories handle the data operations for that aggregate root.

Repositories return domain entities (fully constructed from the data source) and accept domain entities to persist changes. This way, the domain model remains pure Python objects, and the repository translates between those and the persistence layer.

By depending on a repository interface (abstract), the domain and service layer do not depend on the concrete data layer technology. For example, you might define an AbstractRepository interface and have implementations like SqlAlchemyRepository or InMemoryRepository that adhere to it. This follows DIP: the domain code depends on the abstract repository, and the concrete repository depends on database details
bmaingret.github.io
.

Example (Pseudo-code):

class AbstractProductRepository(abc.ABC):
    def add(self, product: Product): ...
    def get(self, sku: str) -> Product: ...

# An adapter implementation using SQLAlchemy (just illustrative, not full code):
class SqlAlchemyProductRepository(AbstractProductRepository):
    def __init__(self, session):
        self.session = session  # e.g., a SQLAlchemy session
    def add(self, product):
        self.session.add(product)
    def get(self, sku):
        return self.session.query(Product).filter_by(sku=sku).one()


In domain or service layer, one would use repo = product_repository (through the abstract interface) to add or get products, unaware of whether it hits a DB, an API, or in-memory store.

Benefits: Repositories make the code more testable (you can swap a fake in-memory repo for tests), and uphold single responsibility (domain objects aren’t concerned with persistence)
bmaingret.github.io
. They also centralize data access logic, which can help with caching and consistency.

Service Layer Pattern

Intent: The Service Layer (or Application Layer or Use Case Layer) organizes and orchestrates use case logic, providing a clear entry point to the system’s operations
bmaingret.github.io
. It coordinates tasks involving multiple domain objects or interactions with external services, while shielding the domain layer from such concerns.

Description: A service layer is typically a set of functions or classes (sometimes called application services) that implement application-specific use cases. Each function in the service layer represents a business use case or transaction script (for instance, “allocate an order to inventory” or “create a new account”). The service layer will:

Validate or sanitize input data (or delegate validation to the domain where appropriate).

Invoke domain operations on the appropriate entities or value objects to perform the business logic.

Coordinate persistence by using repositories (e.g., retrieve or save entities) and possibly handle transactions (often via Unit of Work, see below).

Trigger events or other side effects (e.g. sending notifications) after the core business action, often by publishing domain events to a message bus.

Characteristics:

Orchestration, not Business Rules: The service layer calls into the domain model to execute business rules, but it contains the sequence of steps (workflow) to fulfill a case
bmaingret.github.io
. The actual business invariants and calculations should still live in the domain model (entities/value objects).

Transaction Management: Typically, each service layer operation is executed within a transaction boundary (e.g., start a unit of work at the beginning, commit at the end, or roll back on errors). This ensures consistency if the use case spans multiple repositories or aggregates.

Isolation for Testing: By having thin controllers/UI that delegate to the service layer, you can test the service layer in isolation (supplying fakes for the infrastructure). The book suggests writing the bulk of tests against the service layer (as edge-to-edge tests that include domain + minimal infrastructure)
bmaingret.github.io
. This achieves a good balance of coverage and maintainability.

Multiple Interface Adaptation: The same service layer can serve different interfaces – e.g. a CLI, a REST API, or a GUI can all call the same service functions. This avoids duplicating business logic in multiple controllers.

Example: In a Flask API, an endpoint might translate a JSON request into a command or parameters, then call a function services.allocate(order_id, sku, qty) in the service layer. That function would load the relevant Order and Product from repositories, call methods on the domain entities (like an order.allocate(product, qty) which might raise an OutOfStock exception if not available), save changes via the repositories, and finally return a result or raise a domain exception. If using domain events, the service might also collect events from the domain objects and pass them to the message bus (see Unit of Work and Message Bus below).

Benefits: The service layer clarifies boundaries of each application action (use case)
bmaingret.github.io
. This leads to more maintainable code – one can change internal domain logic without affecting how the outside world calls it, as long as the service layer interface stays the same. It also supports thinner controllers (or other primary adapters) that focus just on translating requests to service calls, and on formatting responses. By concentrating higher-level process logic in one layer, it becomes easier to enforce consistency (all entry points use the same sequence) and to do things like logging, retrying, or permission checks in one place.

Unit of Work (UoW) Pattern

Intent: A Unit of Work maintains a transactional boundary around a set of operations, treating them as a single unit that succeeds or fails together. It helps ensure data integrity and consistency when making changes, especially when multiple repositories or aggregates are involved
bmaingret.github.io
cosmicpython.com
.

Description: In implementation, a UoW often tracks which objects have been loaded and modified during a business transaction and coordinates the writing out of changes (and any necessary locking or version checking). In many ORMs (like SQLAlchemy), the session object already functions as a Unit of Work. The book’s approach is to create an explicit UoW abstraction in the service layer that encapsulates the database session and repositories.

Characteristics:

The UoW is usually used via context management or an explicit start/commit API. For example:

with uow:
    product = uow.products.get(sku)
    order = uow.orders.get(orderid)
    order.allocate(product)
    uow.commit()  # commit transaction (if using explicit commit)


By using a context manager (with uow:), it can automatically handle commit or rollback on exit.

Single Entry Point for Persistence: The Unit of Work provides a single place in the code that knows about starting/committing transactions and the order of these operations
bmaingret.github.io
. Service layer code uses repositories from the UoW rather than directly instantiating repositories. For instance, the UoW might hold repository instances as attributes (uow.orders, uow.products) which share a common database session.

Combining with Domain Events: A UoW implementation can collect domain events from the entities (aggregates) that were modified during the transaction
cosmicpython.com
. After a successful commit, the UoW can then publish these events via the message bus. This ensures that events are only processed if the transaction committed successfully, maintaining consistency between side effects and persisted state.

Error Handling and Rollback: If anything fails during the unit of work, it should roll back the transaction (so no partial changes are saved). This makes error handling easier to reason about – either all the work is done, or none of it is.

In Python, implementing UoW as a context manager (__enter__ opens a transaction, __exit__ commits or rollbacks) is convenient
bmaingret.github.io
. The UoW may wrap an ORM session or even just a transaction on a raw connection.

Benefits: The Unit of Work decouples higher-level logic from the specifics of transaction management. It also prevents accidental partial saves – developers are guided to treat each service action as atomic. By collecting new/changed entities and their events, UoW can coordinate multi-entity operations and event publication cleanly. It further allows easy swapping of transaction strategies (e.g. real database vs. in-memory) for testing by implementing an AbstractUnitOfWork interface and concrete subclasses (similar to repository pattern). Overall, UoW contributes to keeping the domain model persistence-ignorant and maintaining consistency boundaries.

Domain Events and Internal Message Bus

Intent: Use domain events together with a message bus (mediator) to decouple processes within the app and enforce single-responsibility. Instead of a single service function doing many things, events let one part of the code announce that “something happened” and other parts handle the consequences. The internal message bus routes these events (and also commands) to handlers that know what to do
cosmicpython.com
bmaingret.github.io
.

Domain Events Recap: As described, events are raised during domain operations to represent things that occurred (e.g. an OutOfStock event after failing to allocate stock). These events are usually simple data carriers. They might be collected in an entity’s state (e.g. an Aggregate root could have a list of “pending events” it produced), or directly emitted via a domain service or the UoW.

Message Bus (Internal): The message bus is essentially an in-memory publish-subscribe mechanism or mediator within the application process
cosmicpython.com
. It maintains a registry of event types (or command types) to handler functions. When an event is published to the bus, the bus invokes all handlers associated with that event type. For commands, the bus ensures routing to a single appropriate handler.

Handlers: A handler is a function (or method) designed to process a specific event or command
cosmicpython.com
. For example, an event OrderPlaced might be handled by a function that emails the customer and another that adjusts inventory. Each of those would be separate handlers subscribed to OrderPlaced. A command ReorderProduct would have one handler that knows how to perform that action. Handlers typically live in the service layer (or a dedicated “handlers” module) and can call domain logic, other services, or interact with adapters (like sending an email, calling an external API, etc.)
cosmicpython.com
.

Raising and Handling Events: There are a few common ways to integrate events in the flow
bmaingret.github.io
:

The service layer (after performing an action) explicitly publishes events that should be dispatched (e.g. after a successful allocate, publish an Allocated event to the bus).

Domain entities might produce events (like setting self.events.append(SomethingHappened(...)) inside a method). The Unit of Work can gather those and publish them after commit
bmaingret.github.io
.

Some architectures trigger events in response to certain state changes and use the bus immediately (for synchronous handling) or later (for async handling).

Promoting SRP & Modularity: By using events, you avoid a single use-case function from having to know every consequence. For instance, a naive approach to “place order” might also directly send a confirmation email and update analytics — all in one function. With events, the place_order logic only creates an OrderPlaced event. Then one handler sends the email, another updates analytics, etc. This means new reactions can be added without changing the core logic, and responsibilities are divided across multiple units of code
bmaingret.github.io
bmaingret.github.io
. It’s an application of the Open/Closed Principle: new behavior on events can be added without modifying the publisher.

Synchronous vs Asynchronous: Internally, the message bus can operate synchronously (handlers are just called in sequence, possibly on the same thread) which is simplest. But it also enables a move toward asynchronicity or distribution: if later you want to run some handlers in the background or even on separate machines, you can replace or augment the internal bus logic to push to a message broker. The architecture from the book cleanly separates internal events vs external messages – internal events are handled by in-process handlers via the message bus, and some special handlers (or an event publisher adapter) can forward certain events to an external message broker for other services
cosmicpython.com
.

Example: Suppose an Allocation service function allocates a product to an order. If the product’s stock falls to zero, a OutOfStock domain event is generated. We have:

A handler for OutOfStock that sends an email to procurement to reorder stock.

Another handler for OutOfStock that logs the event for analytics.
The service function doesn’t call email or analytics directly; it just triggers the event and commits. The Unit of Work (after commit) or service then calls message_bus.publish(event), and the bus invokes the two handlers. This way, the allocation service is unaware of how many things happen as a result of stock-out, and we can add/remove handlers easily.

Benefits: Using domain events and a message bus leads to looser coupling and better separation of concerns
bmaingret.github.io
. It also makes the flow of the system explicit and traceable – all side effects are driven by event handlers which can be independently understood and tested. When scaling up to a microservices architecture, domain events become natural integration points: the internal events can be serialized and put onto an external message bus (e.g., RabbitMQ, Kafka) so that other services can react to them
cosmicpython.com
. In a monolithic context, the same pattern helps modularize the codebase and possibly run parts of the application in isolation (for example, you could later pull some handlers out into separate processes if needed, without changing how events are defined).

Commands and Command Handlers

Command vs Event Recap: In the context of the message handling system, commands and events are both messages but with a key difference. Commands represent an intention to perform an action (and typically are expected to have exactly one handler), whereas events represent notifications of something that already happened (and may have multiple handlers or none)
cosmicpython.com
. For example, a command might be “ShipOrder” (do this now) whereas an event is “OrderShipped” (this happened).

Command Handlers and the Message Bus: The architecture treats incoming requests as commands that get handled by the same message bus mechanism. Instead of the UI layer directly calling a service function, it may construct a command object and post it to the message bus. The command handler is then a function that carries out the required action, similar to a service function but invoked via the bus routing
cosmicpython.com
. This uniform approach means the application’s entry point (be it a web request or an async message) can simply hand off to the bus.

Distinguishing Commands: It can be useful to formally separate the two kinds of messages in code. For instance, define a base class or marker for commands and another for events. The message bus can use this to enforce that each command has exactly one handler (to avoid ambiguity), while events can fan out to many handlers. The book’s approach eventually models the system as a message-processing application, where everything coming in (whether from an HTTP endpoint or a queue) is handled by the same dispatch system
cosmicpython.com
.

Example: A Flask route POST /allocate might translate the request into a AllocateCommand(order_id, sku, qty) object and call message_bus.handle(command). The message bus looks up the handler for AllocateCommand (say it’s the allocate function in the service layer) and calls it. That function might return a result or raise a domain exception. If it raises an exception (like OutOfStock), the exception could be caught by the Flask layer to return an appropriate HTTP response. Meanwhile, if the allocate function created any events (like OutOfStock event), those would be published on the bus as well, possibly triggering further handlers (such as sending an alert).

Benefits: This pattern further decouples the interface layer from the service layer. The controllers don’t need to know which service function to call; they just send a command to the bus. It also unifies handling of synchronous calls and asynchronous messages (e.g., the same command AllocateCommand could come from a direct API call or from a queue if another service emitted it – in both cases the same handler logic runs). Commands and events flowing through one mechanism simplify the mental model: everything is a message. This makes it easier to add cross-cutting concerns like logging, monitoring, or retry logic in one place (the bus or message handling infrastructure).

Command-Query Responsibility Segregation (CQRS)

Overview: CQRS is an architectural pattern that separates write operations (commands) from read operations (queries). In a traditional layered architecture, the same domain model and database are used to handle both writes and reads. With CQRS, you intentionally split the model: the write side handles transactional updates and emits events, while the read side has one or more query models optimized for fetching data (which could be read-only replicas, cached views, or even different data stores).

In the Book’s Context: After introducing commands and events, the book demonstrates how you might build a simplified query model. For example, after certain events occur, you could maintain a denormalized read model (perhaps a simplified report or a cache) that is easy to query for the UI
cosmicpython.com
. The internal events can update this read model. The idea is to decouple complex domain logic from query concerns – you might not want to run complex domain aggregates just to answer a simple UI query like “how many products are out of stock?” Instead, that could be a separate table or view maintained by events.

When to Use: CQRS adds complexity, so it’s used when read and write characteristics are very different or when the domain logic is complex enough that handling queries through it becomes inefficient or cumbersome. It shines in scenarios where you have high read volume and need specifically tailored read models (possibly using different database technology, like ElasticSearch for search queries, etc.). The book’s example is likely modest, showing a read side that perhaps directly queries the database or a cached projection.

Implementation Notes:

The write side (commands) still uses the patterns above (rich domain model, UoW, events).

The read side might subscribe to certain events (via the message bus). For instance, on an OrderPlaced event, a handler could update a summary table of pending orders, or on ProductCreated event, a handler might index it for search.

The read side can be a simple data-access layer (even raw SQL or a separate ORM model) that is optimized for reads and kept in sync through events. It does not enforce business rules; it’s purely for querying. Sometimes this read model is also called a projection or view model.

Note that CQRS does not necessarily imply Event Sourcing, though events make a convenient bridge between the write and read sides. In our context, we are still using a traditional database for writes (not storing events as the source of truth), but leveraging events to keep read models up to date.

Benefit: When applied appropriately, CQRS can dramatically improve query performance and scalability, and it can simplify the domain model because that model no longer needs to serve ad-hoc querying needs – it only concerns itself with enforcing business invariants on writes. The trade-off is the complexity of maintaining two representations of data and eventual consistency between them (reads might be eventually consistent with writes, if updates propagate via async events).

Dependency Injection and Bootstrapping

Intent: Dependency Injection (DI) is a pattern for providing a class or function with its dependencies from the outside, rather than having it instantiate or import them directly
xiang.es
. The goal is to make dependencies explicit and swappable, improving modularity and testability. Bootstrapping refers to the initialization code that assembles the application components and wires them together (often called the composition root in other languages).

Explicit vs Implicit Dependencies: In Python, it’s common to import modules or use global singletons, which implicitly provides dependencies (e.g. directly importing a database session or calling an email API inside your function)
cosmicpython.com
. However, this makes testing harder – one might resort to monkeypatching or mocks to replace those dependencies
cosmicpython.com
. Instead, the book advocates for passing dependencies as parameters (or constructor args) to the components that need them
cosmicpython.com
. For example, a service layer function might accept an AbstractUnitOfWork or a specific repository as an argument, rather than reaching out to a global variable. This explicit injection allows using a fake or alternative implementation in tests easily
cosmicpython.com
cosmicpython.com
.

Bootstrapping Container: The bootstrap component is responsible for constructing the real implementations of each interface and assembling the application. For instance, at startup, you might create a real database session and pass it to a SqlAlchemyUnitOfWork, create a real message bus with all handlers registered, and set up repositories, then inject those into the service layer or handlers. In the example architecture, instead of letting each request set up its own UoW and message bus, a bootstrapper sets up one configured message bus (with handlers wired) and perhaps a factory for UoWs
cosmicpython.com
cosmicpython.com
. This centralizes object composition.

Pythonic DI: Unlike statically-typed languages with elaborate DI frameworks/containers, in Python dependency injection is often done manually. This can be as simple as passing dependencies through function parameters or initializer arguments. The book’s approach in later chapters uses a bootstrap.py that creates the message bus, UoW, and other adapters, then provides a function to get an entrypoint (service function or command handler) ready to be called with real dependencies
cosmicpython.com
. This is the place where you might decide which implementations to use (e.g. a real email sender vs. a dummy).

Example: Suppose we have an email sending functionality abstracted by AbstractEmailSender with a method send(to, subject). We have ConsoleEmailSender (just prints emails) and SMTPEmailSender (sends real emails). Our order placement handler might depend on AbstractEmailSender. In bootstrap, if we’re in dev mode, we inject a ConsoleEmailSender into that handler; in production, we inject SMTPEmailSender. The handler code just calls email_sender.send(...) without knowing which one it is. In tests, we could inject a mock or dummy easily.

Benefits: DI ensures that policy and business logic are separate from technical details. It helps follow the Open/Closed Principle – e.g., adding a new implementation of a dependency (like switching databases) doesn’t require modifying the core logic, just changing the wiring. Testing is simpler and cleaner as you can provide fake dependencies without monkeypatching or deep patching of internals
cosmicpython.com
cosmicpython.com
. Overall, making dependencies explicit leads to clearer, more maintainable code, at the cost of a bit more verbosity in passing them around. The bootstrapper pattern also keeps the application start-up organized and makes it obvious what the system’s components are.

Testing and Quality Practices

Test-Driven Development (TDD): The book strongly emphasizes TDD to drive design. By writing tests first for the domain model, you ensure the model is decoupled from frameworks (since tests run fast, in memory)
cosmicpython.com
. The patterns above (like repository, UoW, DI) all serve to make the code more test-friendly. For instance, by using an in-memory repository or fake UoW in tests, you can test domain logic without a real database.

High Gear vs Low Gear Testing: A metaphor used is cycling gears – low gear for unit tests (fast, fine-grained) and high gear for broader tests (slower, integration or end-to-end)
bmaingret.github.io
. Aim to cover most logic with fast tests (domain and service layer tests) and use just a few end-to-end tests for the whole system. Guidelines from the book include
bmaingret.github.io
:

One end-to-end test per major feature, to cover integration of layers.

Write the bulk of tests against the service layer, treating it as an “edge-to-edge” test (calling the service or API with faked out infrastructure where possible). This ensures the wiring of domain + application logic works, without the slowness of full end-to-end.

Maintain a small core of true unit tests against the domain model (entities, value objects). You might start with more, but as higher-level tests cover the same cases, you can trim redundant lower-level tests. The idea is to prevent over-specification of internal design while still testing critical business logic.

Test error cases and edge cases as first-class features. For example, test how the system responds when an order can’t be allocated (it should raise OutOfStock, etc.).

Prefer expressing service layer tests in terms of primitive inputs/outputs (like IDs or simple types) rather than internal domain objects. This makes tests more robust to refactoring internal details
bmaingret.github.io
.

Continuous Integration and Quality: Although not the core of the architecture patterns, the book also touches on maintaining a healthy development environment (managing dependencies, using linters/formatters, CI pipelines)
bmaingret.github.io
bmaingret.github.io
. These practices ensure that as the codebase grows in complexity, it remains manageable and consistent.

Evolutionary Design: The authors encourage an iterative approach – start with a simple design and then evolve with patterns as needed. For instance, one might begin with a simple layered MVC in Django, and over time introduce a service layer, then events, then maybe split out a microservice, etc. Each pattern should be introduced to solve a concrete problem (e.g., difficulty testing led to introducing an abstraction, or performance issue on reads led to CQRS). The book’s Epilogue offers advice on refactoring legacy systems towards these patterns gradually
cosmicpython.com
cosmicpython.com
. A key mantra quoted is: “Make the change easy (refactor toward testability/clean architecture); then make the easy change (implement the new feature)”
bmaingret.github.io
.

Summary of Key Components (Cheat Sheet)

Domain Layer: Contains business logic and rules.

Entity: Object with identity, mutable state over time
cosmicpython.com
.

Value Object: Immutable object defined by its values
cosmicpython.com
.

Domain Service: Domain operation not naturally tied to an entity (can be a function).

Aggregate: Cluster of related objects treated as one unit for consistency; has an aggregate root enforcing invariants
cosmicpython.com
.

Domain Event: Record of something that happened in the domain (often leading to side effects)
cosmicpython.com
.

Command: An instruction to perform an action (a use case invocation)
cosmicpython.com
.

Service Layer (Application Layer): Orchestrates use cases and application logic.

Service (Use Case) Functions: Define what the system should do for each operation, coordinate domain objects and repositories
cosmicpython.com
.

Command Handlers: Functions that handle a specific command (often the same as service functions, just invoked via the message bus).

Data Persistence Layer:

Repository: Provides access to aggregate roots, abstracting the data store (e.g., in-memory or database)
cosmicpython.com
.

Unit of Work: Manages transactions and coordinates repositories as a single unit of commit; also collects domain events for dispatch
cosmicpython.com
.

Messaging and Integration:

Internal Message Bus: Routes events and commands to their handlers within the app
cosmicpython.com
.

Handlers: Functions that execute in response to an event or command, performing necessary actions
cosmicpython.com
.

External Event Publisher: Component responsible for publishing certain internal events to an external message broker, for cross-service communication
cosmicpython.com
.

External Message Bus (Broker): Infrastructure (like RabbitMQ, Kafka) that allows different services/applications to communicate via events
cosmicpython.com
. (Not needed for monolith, but conceptually similar patterns apply if integrating bounded contexts.)

Infrastructure (Adapters):

Primary Adapters (Entrypoints): Interface where input enters the system – e.g. web controllers, CLI handlers, message queue consumers. They translate external requests into commands or direct service calls
cosmicpython.com
. For example, a Flask route or a CLI command will create a command object and send it to the service layer (often via the message bus)
cosmicpython.com
.

Secondary Adapters: Implementations of interfaces to external systems – e.g. database ORMs, email senders, payment gateways. These plug into the ports defined by the domain/service layer. They depend on the interface contracts, keeping details isolated
cosmicpython.com
. For instance, an EmailAdapter might implement a EmailSender interface defined in the application layer.
