---
title: Home
layout: home
nav_order: 1
---

# SlideTap Project

## Overview

SlideTap is a comprehensive platform designed for managing and processing digital pathology images and metadata into research  datasets. It provides tools for image preprocessing, metadata management, and project-based workflows. The platform is built using Flask for the web application, Celery for task scheduling and processing, and Node for the web client.

## Features

- **Metadata Management**: Allows importing, exporting, and curating of metadata.
- **Image Processing**: Supports various image processing steps including DICOM conversion and metadata extraction.
- **Project Management**: Facilitates the creation and management of projects, batches, and datasets.


## Components

### Web Client

The web client provides a graphical interface enabling the user to:

- Login to the application
- Create projects and batches
- Search and curate metadata
- Process images
- Finalize projects into datasets

### Web Application

The web application handles the requests from the web client:

- User authentication and authorization
- Project and batch management
- Image and metadata processing

### Task Processing

Long running tasks can be handled in the background using tasks:

- Metadata import and export
- Image preprocessing and postprocessing

### Dataset and Site-Specific Implementation

The platform can, and must, be adopted to the type of dataset to create and the site to extract metadata and images from:

- A schema is used to define the dataset structure
- Metadata and image importers and processors are used to injest site data into the platform
- Metadata and image exporters and processors are used to format curated data into a complete dataset

See #project-implementation and #site-implementation for further details.

## Getting Started

To get started with SlideTap, follow these steps:

1. **Clone the Repository**:
    ```sh
    git clone https://github.com/your-repo/slidetap.git
    cd slidetap
    ```

2. **Set Up Environment Variables**:
    Create a `.env` file with the necessary environment variables:
    ```env
    SLIDETAP_CONFIG_FILE=config.yaml
    SLIDETAP_SECRET_KEY=your_secret_key
    SLIDETAP_DBURI=sqlite:///path/to/your/database.db
    SLIDETAP_STORAGE=/path/to/storage
    SLIDETAP_WEBAPP_URL=http://localhost:5000
    ```

3. **Install Dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

4. **Run the Application**:
    ```sh
    flask run
    ```

5. **Run Celery Worker**:
    ```sh
    celery -A slidetap.task.celery worker --loglevel=info
    ```


## License

SlideTap is licensed under the Apache License, Version 2.0. See the [LICENSE](../LICENSE) file for more details.

