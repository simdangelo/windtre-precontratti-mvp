# Containerization & Docker Run Guide

Yes! You must **always run `docker build` first**. 

Building the image compiles the application, installs dependencies (like Python libraries), and packs headless **LibreOffice**, MS fonts, and your templates directly into the container so that it can run consistently on any machine or in production (like Google Cloud Run).

This guide walks you through building, configuring, and running the application inside a Docker container.

---

## 1. Fast Track (TL;DR)

If you have your `.env` file ready in your project root, run these two commands:

```bash
# Step 1: Build the image (Do this first!)
docker build -t pre-contratti-app .

# Step 2: Run the container with your .env secrets loaded
docker run -p 8080:8080 --env-file .env --name precontratti_run pre-contratti-app
```

---

## 2. Step-by-Step Instructions

### Step 2.1: Create Your `.env` File (If you haven't already)
Create a file named `.env` in the root of your project `/home/user/projects/pre_contratti/` with your Microsoft OneDrive/Graph credentials:

```env
# Microsoft Graph API / OneDrive Credentials
ONEDRIVE_TENANT_ID=your-tenant-id-here
ONEDRIVE_CLIENT_ID=your-client-id-here
ONEDRIVE_CLIENT_SECRET=your-client-secret-here
ONEDRIVE_DRIVE_ID=your-drive-id-here
```

> [!TIP]
> The application code also supports `MS_GRAPH_` prefixed variables as alternatives, making it compatible with existing Dataflow pipeline conventions.

---

### Step 2.2: Build the Container Image
The build process reads the `Dockerfile`, downloads the `python:3.11-slim-bookworm` base OS, installs headless LibreOffice and system fonts, and copies the source code.

Run the build command:
```bash
docker build -t pre-contratti-app .
```

---

### Step 2.3: Start the Container
Start the container and mount the `.env` configuration file directly so that the container has access to your OneDrive API keys:

```bash
docker run -p 8080:8080 --env-file .env --name precontratti_run pre-contratti-app
```

> [!NOTE]
> If you wish to run the container in the background (detached mode), simply add the `-d` flag:
> ```bash
> docker run -d -p 8080:8080 --env-file .env --name precontratti_run pre-contratti-app
> ```

---

## 3. Accessing the Application

Once the container starts, open your web browser and navigate to:

| Endpoint / Page | URL | Description |
| :--- | :--- | :--- |
| **Interactive Admin Portal** | [http://localhost:8080/](http://localhost:8080/) | The premium single-page React dashboard to manage and generate pre-contracts. |
| **Swagger API Docs** | [http://localhost:8080/docs](http://localhost:8080/docs) | Interactive Swagger endpoint explorer to trigger compilation manually. |
| **Redoc API Docs** | [http://localhost:8080/redoc](http://localhost:8080/redoc) | Alternative clean API specification documentation. |

---

## 4. Useful Container Management Commands

### Stop a Running Background Container
```bash
docker stop precontratti_run
```

### Restart the Stopped Container
```bash
docker start precontratti_run
```

### View Live Logs
```bash
docker logs -f precontratti_run
```

### Run an Interactive Shell Inside the Container
If you need to explore files (e.g. check compiled PDFs inside the container's temporary workspace), run:
```bash
docker exec -it precontratti_run bash
```

### Remove the Container
```bash
docker rm precontratti_run
```

---

## 5. Troubleshooting & FAQ

### Port `8080` is Already in Use?
If your local port 8080 is occupied by another application, map the container to a different external port (for example, `9090`):
```bash
docker run -p 9090:8080 --env-file .env --name precontratti_run pre-contratti-app
```
Then access the portal at [http://localhost:9090/](http://localhost:9090/).

### How does the Fallback behave inside Docker?
* **With `.env` Credentials:** The container will connect to Microsoft Graph API and synthesize premium Word templates directly to PDFs via OneDrive.
* **Without `.env` Credentials:** The container falls back to its built-in headless LibreOffice binary to render PDFs locally. No features are blocked!
