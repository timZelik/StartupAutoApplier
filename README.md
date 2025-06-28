# Startup Job Automator

An automated tool for applying to jobs on workatastartup.com using browser automation.

## Features

- Automated login to workatastartup.com
- Job search with customizable filters
- Automated application submission
- Headless browser support for cloud deployment
- Detailed logging and error handling

## Prerequisites

- Python 3.8+
- Playwright (will be installed automatically)
- Work at a Startup account

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/startup-job-automator.git
   cd startup-job-automator
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

5. Copy the example environment file and update with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Configuration

Edit the `.env` file with your settings:

```
# Work at a Startup credentials
WORK_AT_A_STARTUP_EMAIL=your_email@example.com
WORK_AT_A_STARTUP_PASSWORD=yourpassword

# Application settings
MAX_APPLICATIONS=5       # Maximum number of applications per run
HEADLESS=false           # Set to true for cloud deployment
DEBUG=true               # Enable debug logging
```

## Usage

### Running Locally (Visible Browser)

```bash
python cli.py
```

### Running in Headless Mode (Cloud)

```bash
HEADLESS=true python cli.py
```

### Running with Custom Settings

```bash
MAX_APPLICATIONS=3 HEADLESS=true python cli.py
```

## Deployment

### Docker

1. Build the Docker image:
   ```bash
   docker build -t job-automator .
   ```

2. Run the container:
   ```bash
   docker run -e WORK_AT_A_STARTUP_EMAIL=your_email@example.com \
              -e WORK_AT_A_STARTUP_PASSWORD=yourpassword \
              -e HEADLESS=true \
              job-automator
   ```

### Cloud Providers

#### AWS Lambda with EFS
1. Package the application and dependencies
2. Set up an EFS filesystem for browser storage
3. Configure Lambda with the EFS mount
4. Set up EventBridge to trigger the Lambda on a schedule

#### Google Cloud Run
1. Package the application in a container
2. Deploy to Cloud Run
3. Set up Cloud Scheduler to trigger the job

## Logs

Logs are written to `automation.log` in the project directory.

## License

MIT

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with workatastartup.com's terms of service.
