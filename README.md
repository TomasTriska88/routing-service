# Country Routing Service

A robust, modern Spring Boot 3.3.0 REST service built on Java 21 (LTS) that calculates the shortest land route (fewest border crossings) between two countries using a Breadth-First Search (BFS) algorithm.

---

## 🏗️ Architectural Overview

This service is designed with clean architecture principles, emphasizing performance, robustness, and testability.

```
                  ┌──────────────────────┐
                  │   Remote Countries   │
                  │   JSON (GitHub)      │
                  └──────────┬───────────┘
                             │ (Attempts remote fetch)
                             ▼
 ┌─────────────┐  ┌──────────────────────┐  (Fallback)  ┌──────────────────────┐
 │             │  │                      ├─────────────>│   Local Classpath    │
 │   Clients   │  │    RoutingService    │              │   countries.json     │
 │   (HTTP)    │  │                      │              └──────────────────────┘
 └──────┬──────┘  └──────────┬───────────┘
        │                    │ (Builds in-memory Adjacency List graph)
        │ GET /routing/...   ▼
        │                 ┌──────────────────────┐
        └────────────────>│  Adjacency List Map  │
                          │   (ConcurrentHash)   │
                          └──────────────────────┘
```

### 1. High Performance & Offline Resilience
* **Startup Initialization**: The country border database is loaded **once** at application startup. By default, it fetches the JSON dataset asynchronously from GitHub.
* **Offline Classpath Fallback**: If the remote server is down, unreachable, or the application is run in an offline development environment, the service automatically falls back to loading a bundled copy of `countries.json` from the classpath.
* **In-Memory Graph**: Once parsed, the database is mapped into a thread-safe `ConcurrentHashMap<String, List<String>>` acting as an adjacency list. All incoming routing queries are solved instantly from memory, avoiding slow external API calls.

### 2. Graph Routing Algorithm
* Since all borders represent equal distance (weight = 1), **Breadth-First Search (BFS)** is utilized.
* BFS guarantees finding the shortest path in an unweighted graph in $O(V + E)$ time complexity (where $V$ is the number of countries and $E$ is the number of border connections).

### 3. REST API & Exception Mapping
* The service exposes the REST endpoint `/routing/{origin}/{destination}`.
* Validation checks ensure both parameters are valid country codes.
* If a path is unreachable (islands like Madagascar) or inputs are invalid (unknown country codes), the application throws tailored exceptions which are intercepted by a `GlobalExceptionHandler` to return `HTTP 400 Bad Request` with structured JSON error details.

---

## 🚀 Getting Started

### Prerequisites
* **Java 21 (JDK)**
* **Docker** (Optional, for containerized execution)

*Note: You do not need Maven installed. The project includes a Maven Wrapper (`mvnw` / `mvnw.cmd`) which automatically downloads and configures Maven on first run.*

---

## 🛠️ Build & Run Instructions

### 1. Run Locally
To compile and start the Spring Boot application on port `8080`, execute:

**Windows Command Prompt / PowerShell:**
```powershell
./mvnw.cmd spring-boot:run
```

**Linux / macOS:**
```bash
chmod +x mvnw
./mvnw spring-boot:run
```

### 2. Run in Docker
To build the multi-stage Docker image and start the container on port `8080` in a single command, run:

```bash
docker compose up --build
```

---

## 🧪 Running Tests

The project features comprehensive unit tests for the BFS routing engine (including edge case validation) and WebMvc integration tests for the REST controllers.

To run the full test suite, execute:

```bash
./mvnw.cmd test
```

---

## 📖 API Usage Examples

### 1. Successful Land Route Query
Find the shortest path from the Czech Republic (`CZE`) to Italy (`ITA`):

**Request:**
```bash
curl -i http://localhost:8080/routing/CZE/ITA
```

**Response (`HTTP 200 OK`):**
```json
{
  "route": [
    "CZE",
    "AUT",
    "ITA"
  ]
}
```

### 2. Unreachable Destination (Island Nation)
Querying a route from the Czech Republic (`CZE`) to Madagascar (`MDG`):

**Request:**
```bash
curl -i http://localhost:8080/routing/CZE/MDG
```

**Response (`HTTP 400 Bad Request`):**
```json
{
  "status": 400,
  "message": "No land route found between CZE and MDG",
  "timestamp": "2026-06-04T14:35:53.637"
}
```

### 3. Invalid Country Code Input
Querying a route with a non-existent country code:

**Request:**
```bash
curl -i http://localhost:8080/routing/CZE/XYZ
```

**Response (`HTTP 400 Bad Request`):**
```json
{
  "status": 400,
  "message": "Destination country code 'XYZ' is not a valid country",
  "timestamp": "2026-06-04T14:35:54.128"
}
```

### 4. Same Origin and Destination
**Request:**
```bash
curl -i http://localhost:8080/routing/CZE/CZE
```

**Response (`HTTP 200 OK`):**
```json
{
  "route": [
    "CZE"
  ]
}
```
