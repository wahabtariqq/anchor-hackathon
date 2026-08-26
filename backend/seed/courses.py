"""The 10 pre-seeded catalog courses (PRD §6.2), each with 120-200 words of curriculum text.

This list is the producer. contracts/fixtures/courses.json is a copy of what GET /api/courses
returns from it, and the frontend builds against that copy — regenerate it in the same commit:

    python -c "import json; from seed.courses import CATALOG; \
               print(json.dumps({'courses': CATALOG}, indent=2, ensure_ascii=False))" \
        > ../contracts/fixtures/courses.json

Loaded into the `course` table by scripts/seed_db.py.
"""

CATALOG: list[dict[str, str]] = [
    {
        "id": "cs201",
        "code": "CS201",
        "name": "Data Structures & Algorithms",
        "curriculum_text": (
            "Arrays, linked lists, stacks, queues, trees, and graphs; asymptotic (Big-O, Big-Theta) "
            "analysis of time and space; recursion and divide-and-conquer; sorting algorithms "
            "(insertion, quicksort, mergesort, heapsort, counting sort) and their tradeoffs; hash "
            "tables, hash function design, and collision handling by chaining and open addressing; "
            "binary search trees and balanced trees (AVL, red-black); heaps and priority queues; graph "
            "representations, traversal (BFS/DFS), topological sort, shortest paths (Dijkstra, "
            "Bellman-Ford), and minimum spanning trees (Kruskal, Prim); greedy algorithms and exchange "
            "arguments; dynamic programming over sequences, grids, and subsets, with memoization and "
            "tabulation; union-find with path compression; amortized analysis; string matching; an "
            "introduction to NP-completeness and reductions. Weekly problem sets are implemented in a "
            "systems language and graded on both correctness and measured complexity. Students finish "
            "able to pick a data structure from a problem statement and defend the choice."
        ),
    },
    {
        "id": "cs202",
        "code": "CS202",
        "name": "Object-Oriented Programming",
        "curriculum_text": (
            "Classes, objects, encapsulation, inheritance, composition, and polymorphism; interfaces and "
            "abstract classes; static and dynamic dispatch; generics and type parameters; design "
            "patterns (factory, builder, observer, strategy, decorator, adapter, singleton) and when "
            "each is the wrong choice; UML class, sequence, and state diagrams; the SOLID principles and "
            "dependency inversion; refactoring toward smaller objects; unit testing, test doubles, and "
            "test-driven development; exception handling and error-signalling strategy; object "
            "lifecycle, copy semantics, and basic memory management including garbage collection and "
            "reference counting; equality, hashing, and immutability contracts; package structure and "
            "API design for reuse. A semester-long team project builds a mid-sized application from a "
            "written requirement using a shared repository, branch-per-feature version control, and peer "
            "code review; grading covers design quality and test coverage, not only working output. "
            "Weekly labs convert procedural code into an object model and argue the tradeoff."
        ),
    },
    {
        "id": "cs301",
        "code": "CS301",
        "name": "Database Management Systems",
        "curriculum_text": (
            "Relational model and relational algebra; ER modeling and schema design; SQL in depth \u2014 "
            "joins, subqueries, set operations, aggregation, grouping, and window functions; views and "
            "common table expressions; normalization from 1NF to BCNF and the cases for deliberate "
            "denormalization; physical storage, B-tree and hash indexing, and reading query execution "
            "plans; the basics of query optimization, cardinality estimation, and join ordering; "
            "transactions, the ACID properties, isolation levels, and the anomalies each permits; "
            "concurrency control by two-phase locking and multiversion concurrency control; deadlock "
            "handling; write-ahead logging, recovery, and backups; stored procedures and triggers; an "
            "introduction to document, key-value, and column stores, and when to reach for them instead. "
            "A semester project designs a multi-table schema from a domain description, loads realistic "
            "data, and tunes a set of slow queries with indexes and rewrites; students present "
            "before-and-after execution plans."
        ),
    },
    {
        "id": "cs302",
        "code": "CS302",
        "name": "Operating Systems",
        "curriculum_text": (
            "Process and thread models, context switching, and the process lifecycle; CPU scheduling "
            "(round-robin, priority, multilevel feedback, completely fair) and how each starves; "
            "synchronization primitives \u2014 mutexes, semaphores, condition variables, and barriers \u2014 "
            "applied to the classic concurrency problems; race conditions, atomicity, and memory "
            "visibility; deadlock detection, prevention, and avoidance; virtual memory, paging, "
            "page-replacement policies, and thrashing; memory allocators; file system layout, inodes, "
            "journalling, and I/O scheduling; buffering and caching; interprocess communication by "
            "pipes, shared memory, signals, and sockets; system calls and the user/kernel boundary; "
            "interrupts and device drivers; an introduction to virtualization and containers. Labs are "
            "written in C against a Unix-like kernel: a shell with job control, a thread-safe allocator, "
            "a producer-consumer pipeline, and a user-level thread scheduler. Debugging with gdb, "
            "strace, and valgrind is examined."
        ),
    },
    {
        "id": "cs303",
        "code": "CS303",
        "name": "Computer Networks",
        "curriculum_text": (
            "The OSI and TCP/IP layering models and the end-to-end argument; the physical and link "
            "layers, framing, error detection, Ethernet, and switching; IP addressing, subnetting, CIDR, "
            "NAT, and IPv6; intra- and inter-domain routing (link-state, distance-vector, and BGP at a "
            "high level); the transport layer in depth \u2014 UDP, TCP connection setup and teardown, "
            "reliable delivery, flow control, and congestion control (slow start, AIMD, and modern "
            "variants); the application layer \u2014 HTTP/1.1 and HTTP/2, DNS resolution, TLS handshakes, "
            "email and file-transfer protocols; socket programming and the client-server model; network "
            "security fundamentals including certificates, firewalls, and common attacks; an "
            "introduction to distributed-systems tradeoffs of latency, partition tolerance, and "
            "consistency. Labs build a concurrent client-server application over raw sockets and a "
            "reliable-transfer protocol on top of UDP, and require capturing and explaining real traffic "
            "in a packet analyser."
        ),
    },
    {
        "id": "cs401",
        "code": "CS401",
        "name": "Machine Learning",
        "curriculum_text": (
            "Supervised learning: linear and logistic regression, regularized variants, k-nearest "
            "neighbours, naive Bayes, decision trees, random forests, gradient boosting, and support "
            "vector machines with kernels; unsupervised learning: k-means and hierarchical clustering, "
            "density-based clustering, PCA and dimensionality reduction; model evaluation \u2014 "
            "train/validation/test splits, k-fold cross-validation, precision, recall, F1, ROC and "
            "precision-recall curves, confusion matrices, and choosing a metric for imbalanced data; "
            "feature engineering, encoding, scaling, and feature selection; the bias-variance tradeoff, "
            "overfitting, and learning curves; hyperparameter search; loss functions, gradient descent "
            "and its variants, and an introduction to feedforward neural networks and backpropagation; "
            "the linear algebra, calculus, and probability the above rests on; data leakage and "
            "reproducibility. Coursework is in Python with standard numerical and ML libraries; a final "
            "project trains, tunes, and evaluates a model on a real dataset and reports honest error "
            "analysis."
        ),
    },
    {
        "id": "cs402",
        "code": "CS402",
        "name": "Web Development",
        "curriculum_text": (
            "HTTP fundamentals \u2014 methods, status codes, headers, cookies, caching, and the "
            "request/response cycle; client-server architecture and the same-origin policy with CORS; "
            "designing and building REST APIs: routing, request validation, pagination, error contracts, "
            "versioning, and authentication with sessions and tokens; server-side data access and "
            "connecting an API to a relational database; frontend implementation with a component-based "
            "framework \u2014 components, props, state, effects, and lists; client-side state management and "
            "data fetching; forms, validation, and accessibility basics; responsive layout with modern "
            "CSS, flexbox, and grid; asset bundling and build tooling; environment configuration and "
            "secret handling; deployment of a two-service application, logging, and basic observability; "
            "an introduction to web security (XSS, CSRF, injection) and to WebSockets for live updates. "
            "A semester project ships a full-stack CRUD application with a real database, deployed to a "
            "public URL and reviewed on both API design and interface quality."
        ),
    },
    {
        "id": "cs403",
        "code": "CS403",
        "name": "Software Engineering",
        "curriculum_text": (
            "The software development lifecycle and its common process models; eliciting, writing, and "
            "prioritising requirements, user stories, and acceptance criteria; estimation and planning; "
            "software architecture \u2014 layering, modularity, coupling and cohesion, architectural "
            "patterns, and documenting a design with diagrams and decision records; design patterns in "
            "the large; version control workflows, trunk-based development and branch-per-feature, code "
            "review practice, and merge strategy; testing at every level \u2014 unit, integration, contract, "
            "system, and regression \u2014 plus coverage, test doubles, and flaky-test triage; continuous "
            "integration and continuous delivery pipelines, build reproducibility, and release "
            "management; agile practice: sprints, standups, backlog grooming, retrospectives, and "
            "velocity; technical debt, refactoring, and legacy-code strategy; defect tracking, incident "
            "response, and postmortems; software licensing and professional ethics. A semester-long team "
            "project runs as real sprints against a genuine external stakeholder, with a working "
            "increment demonstrated at the end of each iteration."
        ),
    },
    {
        "id": "cs404",
        "code": "CS404",
        "name": "Probability & Statistics",
        "curriculum_text": (
            "Probability axioms, sample spaces, combinatorics, conditional probability, independence, "
            "and Bayes' theorem; discrete and continuous random variables; the binomial, geometric, "
            "Poisson, uniform, exponential, and normal distributions and where each arises; joint, "
            "marginal, and conditional distributions; expectation, variance, covariance, and "
            "correlation; transformations and sums of random variables; the law of large numbers and the "
            "central limit theorem; sampling distributions; point estimation, maximum likelihood, bias, "
            "and standard error; confidence intervals; hypothesis testing, p-values, type I and type II "
            "error, power, and multiple-comparison correction; t-tests, chi-square tests, and ANOVA; "
            "simple and multiple linear regression, residual diagnostics, and interpretation of "
            "coefficients; the design and analysis of A/B tests, including sample-size calculation and "
            "common pitfalls; an introduction to Bayesian inference. Problem sets pair hand calculation "
            "with statistical software, and a final assignment analyses a real dataset and defends its "
            "conclusions."
        ),
    },
    {
        "id": "cs405",
        "code": "CS405",
        "name": "Computer Vision",
        "curriculum_text": (
            "Image formation, camera models, projection, and digital image representation; colour spaces "
            "and histograms; point operations, filtering, convolution, and frequency-domain analysis; "
            "noise models and denoising; edge detection (Sobel, Canny), corner and blob detection, and "
            "local feature descriptors with matching; image pyramids and scale space; segmentation by "
            "thresholding, clustering, region growing, and graph cuts; morphological operations; "
            "classical object detection and recognition with sliding windows and hand-crafted features; "
            "convolutional neural networks for classification, detection, and semantic segmentation, "
            "including transfer learning from pretrained backbones; data augmentation, labelling "
            "strategy, and dataset bias; camera calibration, homographies, stereo correspondence, depth "
            "estimation, and basic structure from motion; optical flow and tracking across frames; "
            "evaluation metrics such as IoU and mean average precision. A final project curates an image "
            "dataset, trains a vision model, and reports quantitative results with failure-case "
            "analysis."
        ),
    },
]
