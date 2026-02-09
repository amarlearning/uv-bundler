# uv-pack 📦

**The Universal Cross-Platform Packager for Python.**

`uv-pack` is a high-performance CLI tool designed to bridge the gap between local development and enterprise production environments. It enables developers to build **Linux-ready JARs, PEX files, and Zipapps** from any machine (macOS, Windows, or Linux) without needing Docker or remote build servers.

## 🚀 The Problem: "The Platform Tax"

Enterprise data environments (Spark, Flink, AWS Lambda) often run on different architectures than developer laptops.

* **Infrastructure Friction:** Organizations maintain expensive Linux "Build Runners" just to package artifacts for Linux.
* **Architecture Lock-in:** Switching to cost-efficient hardware like **AWS Graviton (ARM)** is difficult because build pipelines are hard-coded to Intel/AMD chipsets.
* **Fragile Deployments:** Native extensions (NumPy, Pandas) often crash due to OS mismatches when bundled using simple ZIP hacks.

## ✨ Key Features

* **Zero-Config Cross-Packaging:** Build for `linux-x86_64` or `linux-aarch64` directly from your MacBook.
* **Powered by `uv`:** Leverages the world's fastest resolver and downloader for near-instant builds.
* **Dual-Identity Artifacts:** Produces JARs that are fully compatible with the JVM (Spark/Flink) while remaining native to Python.
* **Architecture Aware:** Automatically identifies and fetches the correct "Manylinux" wheels for your target destination.

---

## 🛠 Installation

```bash
# Clone the repository
git clone [https://github.com/your-username/uv-pack.git](https://github.com/your-username/uv-pack.git)
cd uv-pack

# Install in editable mode
pip install -e .
```

> Note: Requires uv to be installed on your path.

---
## 📖 Usage

### 1. Build a Fat JAR for Apache Spark (Linux ARM64). If you are on a Mac and need to deploy a job to an AWS Graviton Spark cluster:
```bash
  uv-pack build \
  --project ./my-data-job \
  --target spark-jar \
  --platform linux \
  --arch aarch64 \
  --output ./dist/job.jar
```

### 2. Build a PEX Executable for Airflow
```bash
  uv-pack build \
  --project ./analytics-task \
  --target pex \
  --platform linux \
  --arch x86_64 \
  --output ./dist/task.pex
```

---
## 🏗 How it Works
1. **Resolution**: uv-pack uses uv to resolve a dependency graph for your target OS, not your local OS.
2. **Fetch**: It downloads the specific platform-compatible Wheels (.whl).
3. **Assembly**: It bundles your source code, the fetched dependencies, and the necessary metadata (like MANIFEST.MF for JARs) into a single optimized artifact.

---
## 🗺 Roadmap
- **[ ] Phase 1**: Core CLI with uv integration for cross-platform resolution.
- **[ ] Phase 2**: JAR assembly with Java Manifest support.
- **[ ] Phase 3**: Support for AWS Lambda Layer packaging.
- **[ ] Phase 4**: Integration with uv Workspaces for monorepo support.

---
## 🤝 Contributing
We welcome contributions! If you've felt the pain of "it works on my machine but fails on the cluster," this tool is for you.

1. Fork the repo.
2. Create your feature branch.
3. Open a Pull Request.

## 📜 License
[Apache License 2.0](./LICENSE)
