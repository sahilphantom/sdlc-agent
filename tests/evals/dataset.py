"""
Evaluation Dataset for Phase 2 Core Agents.
Contains 10 diverse PRD samples to test the robustness of the PRD → Review loop.
"""

PRD_DATASET = [
    {
        "id": "PRD-001",
        "name": "Todo REST API",
        "text": "Build a REST API for a todo application. Features: user auth, CRUD for todos, filter by status. Tech: FastAPI, PostgreSQL."
    },
    {
        "id": "PRD-002",
        "name": "URL Shortener",
        "text": "Create a URL shortener service. Users submit a long URL and get a short code. When visiting the short code, redirect to the original. Track click counts. Tech: Node.js, Redis."
    },
    {
        "id": "PRD-003",
        "name": "Markdown to HTML CLI",
        "text": "Build a command-line tool that takes a markdown file path as input and outputs the rendered HTML to stdout or a file. Support basic markdown: headers, bold, lists, and code blocks. Tech: Python, Click."
    },
    {
        "id": "PRD-004",
        "name": "E-commerce Cart",
        "text": "Create a shopping cart microservice. Features: add item, remove item, update quantity, calculate total price with tax. Tech: Go, in-memory storage."
    },
    {
        "id": "PRD-005",
        "name": "Weather Dashboard",
        "text": "Build a frontend weather dashboard. Fetches data from OpenWeather API based on user city input. Displays current temperature, humidity, and a 5-day forecast. Tech: React, TailwindCSS."
    },
    {
        "id": "PRD-006",
        "name": "Real-time Chat",
        "text": "Build a simple real-time chat application. Users can join rooms and send messages. Messages should appear instantly for all users in the room. Tech: Python, WebSockets."
    },
    {
        "id": "PRD-007",
        "name": "Expense Tracker",
        "text": "Create a personal expense tracker. Users can log expenses with categories (food, transport, etc.), view a list of recent expenses, and see a monthly summary chart. Tech: Next.js, SQLite."
    },
    {
        "id": "PRD-008",
        "name": "Blog Engine",
        "text": "Build a simple blog engine. Features: create posts with markdown, list posts, view single post, and add comments. Tech: Django, PostgreSQL."
    },
    {
        "id": "PRD-009",
        "name": "JWT Auth Service",
        "text": "Create a standalone authentication microservice. Endpoints for register, login, and refresh token. Passwords must be hashed. Tech: Rust, Actix-web."
    },
    {
        "id": "PRD-010",
        "name": "File Upload Service",
        "text": "Build a file upload service. Users upload a CSV file, the system parses it, validates the schema, and stores the records in a database. Return a success/failure report. Tech: Python, MinIO/S3."
    }
]