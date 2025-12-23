# 🎮 Game Industry Market Analysis

> A powerful data pipeline for scraping, analyzing, and visualizing gaming market trends using SteamSpy data.

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Marimo](https://img.shields.io/badge/marimo-0.18.4-orange.svg)](https://marimo.io/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [Step 1: Install UV](#step-1-install-uv)
  - [Step 2: Clone the Repository](#step-2-clone-the-repository)
  - [Step 3: Setup Environment](#step-3-setup-environment)
- [Usage](#-usage)
  - [Running the Scraper](#running-the-scraper)
  - [Running Visualizations](#running-visualizations)
  - [Development Mode](#development-mode)
- [Configuration](#-configuration)
- [Data Output](#-data-output)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

---

## 🎯 Overview

This project provides an automated pipeline for collecting and analyzing gaming market data from SteamSpy. Built with modern async Python and interactive Marimo notebooks, it enables market research, trend analysis, and data-driven decision making for game developers and industry analysts.

**Current Capabilities:**
- 🚀 High-performance async scraping with rate limiting
- 📊 Interactive data visualization with Marimo notebooks
- 💾 Automatic daily data organization
- 🔄 Resumable scraping with progress tracking
- 📈 Genre and tag frequency analysis

---

## ✨ Features

- **Async Architecture**: Efficient concurrent data fetching with `aiohttp`
- **Rate Limiting**: Respectful API usage with configurable delays
- **Progress Tracking**: Resume interrupted scrapes without data loss
- **Interactive Notebooks**: Marimo-powered reactive analysis
- **Clean Architecture**: Modular design with base scraper class for extensibility
- **Error Handling**: Comprehensive logging and error recovery
- **Daily Organization**: Automatic date-based data storage

---

## 📁 Project Structure

```
steamscraping/
├── 📂 Data/                      # Generated during scraping
│   └── 📂 YYYY-MM-DD/            # Daily data folders
│       ├── steamspy_data.jsonl   # Main dataset (JSON Lines)
│       ├── scraped_appids.txt    # Progress tracking
│       ├── metadata.json         # Scrape session info
│       └── steamspy_errors.log   # Error logs
├── 📂 src/                       # Source code
│   ├── BaseScraper.py            # Abstract base scraper
│   ├── FileSystem.py             # File I/O operations
│   └── SteamSpyScraper.py        # SteamSpy implementation
├── 📂 .vscode/                   # VS Code configuration
│   ├── launch.json               # Debug configurations
│   ├── settings.json             # Editor settings
│   └── tasks.json                # Build tasks
├── main.py                       # Scraper notebook
├── visualization.py              # Analysis notebook
├── pyproject.toml                # Project dependencies
├── .python-version               # Python version (3.13)
└── README.md                     # You are here!
```

---

## 📋 Prerequisites

- **Operating System**: Windows, macOS, or Linux
- **Python**: 3.13+ (automatically managed by UV)
- **Internet**: Stable connection for API requests
- **Disk Space**: ~100MB per 10,000 apps scraped

---

## 🚀 Installation

### Step 1: Install UV

UV is a fast Python package installer and resolver. Choose your platform:

#### **Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### **macOS/Linux**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### **Verify Installation**
```bash
uv --version
```

> 💡 **Tip**: Restart your terminal after installation to ensure UV is in your PATH.

---

### Step 2: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/Icewav3/SteamScraping
cd steamscraping
```

Or download and extract the ZIP file, then navigate to the folder:
```bash
cd path/to/steamscraping
```

---

### Step 3: Setup Environment

UV will automatically create a virtual environment and install all dependencies:

```bash
# Install all dependencies
uv sync
```

This command:
- ✅ Creates a `.venv` folder with Python 3.13
- ✅ Installs `marimo`, `aiohttp`, and `tqdm`
- ✅ Sets up the project for immediate use

---

## 💻 Usage

### Running the Scraper

Launch the interactive Marimo scraper notebook:

```bash
uv run marimo edit main.py
```

This opens an interactive notebook in your browser where you can:
- Configure scraping parameters (pages, delays)
- Start/stop the scraper
- Monitor real-time progress
- View scraping statistics

**Command Line Alternative** (headless mode):
```bash
uv run marimo run main.py
```

---

### Running Visualizations

Analyze collected data with the visualization notebook:

```bash
uv run marimo edit visualization.py
```

**Features:**
- 📊 Genre distribution analysis
- 🏷️ Tag frequency charts
- 📈 Market trend visualization
- 🎨 Interactive Seaborn plots

---

### Development Mode

#### **Using VS Code**

1. Open the project in VS Code
2. Install the [Marimo extension](https://marketplace.visualstudio.com/items?itemName=marimo-team.vscode-marimo)
3. Press `F5` to launch with debugger attached

#### **Manual Development Server**

```bash
# Run with auto-reload on file changes
uv run marimo edit main.py --watch --port 8888

# Run in sandbox mode (isolated execution)
uv run marimo edit main.py --sandbox
```

---

## ⚙️ Configuration

### Scraper Parameters

Edit these in `main.py` or pass to `SteamSpyScraper()`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pages` | `10` | Number of pages to scrape (~1000 apps each) |
| `page_delay` | `15.0` | Seconds between page requests |
| `app_delay` | `0.1` | Seconds between app detail requests |
| `suppress_output` | `False` | Hide console output |

**Example:**
```python
async with SteamSpyScraper(
    fs, 
    pages=20,           # Scrape 20 pages (~20,000 apps)
    page_delay=10,      # Wait 10s between pages
    app_delay=0.2       # Wait 0.2s between apps
) as scraper:
    await scraper.scrape()
```

---

## 📦 Data Output

### File Formats

#### **`steamspy_data.jsonl`**
JSON Lines format - one game per line:
```json
{"appid": 730, "name": "Counter-Strike 2", "developer": "Valve", "owners": "100,000,000 .. 200,000,000", ...}
{"appid": 570, "name": "Dota 2", "developer": "Valve", "owners": "50,000,000 .. 100,000,000", ...}
```

#### **`metadata.json`**
Scrape session information:
```json
{
  "start_time": "2024-12-12T10:30:00",
  "end_time": 1702384500.123,
  "pages_scraped": 10,
  "apps_scraped": 8547
}
```

#### **`scraped_appids.txt`**
List of completed app IDs for resume functionality:
```
730
570
440
...
```

---

## 🔧 Troubleshooting

### Common Issues

#### **`uv: command not found`**
- **Solution**: Restart your terminal or add UV to PATH manually
- **Windows**: `%USERPROFILE%\.cargo\bin`
- **Unix**: `~/.cargo/bin`

#### **Rate Limit Errors (HTTP 429)**
- **Solution**: Increase `page_delay` and `app_delay` values
- SteamSpy allows ~1 request per second

#### **Progress Bar Not Showing in Browser**
- **Known Issue**: Marimo progress bars may not render in all browsers
- **Workaround**: Check console output or use `suppress_output=False`

#### **Missing Data Directory**
- Automatically created on first run
- If deleted, will be recreated

#### **Port Already in Use**
```bash
# Use a different port
uv run marimo edit main.py --port 8889
```

---

## 🗺️ Roadmap

### 🔥 High Priority
- [ ] Complete Marimo migration for native progress bar support
- [ ] Implement data integrity checking script
- [ ] Create time-series comparative analysis notebook
- [ ] Remove unused dependencies

### 🎯 Medium Priority
- [ ] Add multiple data source support (IGDB, Steam Store API)
- [ ] Implement async multi-scraper coordination
- [ ] Design data merging strategy for multi-source accuracy

### 💡 Low Priority
- [ ] Enhanced UI with scraper control buttons
- [ ] Advanced genre/tag correlation analysis
- [ ] Export to CSV/Excel formats

### 🚀 Long Term
- [ ] Cloud deployment for 24/7 scraping (free tier)
- [ ] Automated backup system (GitHub/cloud storage)
- [ ] Machine learning for market trend prediction
- [ ] Real-time dashboard with live updates

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Test thoroughly**
   ```bash
   uv run marimo edit main.py
   ```
5. **Commit with clear messages**
   ```bash
   git commit -m "Add amazing feature"
   ```
6. **Push and create a Pull Request**
   ```bash
   git push origin feature/amazing-feature
   ```

### Code Style
- Follow PEP 8 guidelines
- Use type hints where possible
- Document all public functions
- Keep modules focused and modular

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **[SteamSpy](https://steamspy.com/)** - API provider
- **[Marimo](https://marimo.io/)** - Reactive notebook framework
- **[UV](https://github.com/astral-sh/uv)** - Fast Python package manager

---

## 📞 Support

Having issues? Here's how to get help:

1. **Check [Troubleshooting](#-troubleshooting)** section
2. **Search existing issues** on GitHub
3. **Create a new issue** with:
   - Error message
   - Steps to reproduce
   - System info (`uv --version`, OS)

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ and ☕ for the gaming community

</div>
