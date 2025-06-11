---
title: Home
layout: home
nav_order: 1
---

# SlideTap Project

## Overview

SlideTap is a comprehensive platform designed for managing and processing digital pathology images and metadata into research  datasets. It provides tools for image preprocessing, metadata management, and project-based workflows. The platform is built using FastAPI for the web application, Celery for task scheduling and processing, and Node for the web client.

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

See [tasks](task.md) for more information.

### Dataset and Site-Specific Implementation

The platform can, and must, be adopted to the type of dataset to create and the site to extract metadata and images from:

- A schema is used to define the dataset structure
- Metadata and image importers and processors are used to injest site data into the platform
- Metadata and image exporters and processors are used to format curated data into a complete dataset

See [site implementations](site_implementations.md) and [dataset implementations](dataset_implementations.md) for further details.

## Example application

For an ready-made example application, see [example](example.md).

## License

*SlideTap*: Copyright 2024 Sectra AB, licensed under Apache 2.0.

## Acknowledgement

This project is part of a project that has received funding from the Innovative Medicines Initiative 2 Joint Undertaking under grant agreement No 945358. This Joint Undertaking receives support from the European Union’s Horizon 2020 research and innovation programme and EFPIA. IMI website: <www.imi.europa.eu>
