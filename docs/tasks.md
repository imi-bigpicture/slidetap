---
title: Tasks
layout: home
nav_order: 5
---

## Background task

Preferably the import and export of images and metadata should be performed as background tasks. For this following implementations can be used:

- [`BackgroundMetadataImporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/importer/metadata_importer.py) togeter with a [`MetadataImportProcessor`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/metadata/metadata_import_processor.py).
- [`BackgroundImageImporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/importer/image_importer.py) together with a [`ImageDownloader`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/image/image_downloader.py) and/or [`ImagePreProcessor`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/image/image_processor.py).
- [`BackgroundImageExporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/exporter/image_exporter.py) together with a ['ImagePostProcessor'](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/image/image_processor.py).
- [`BackgroundMetadataExporter`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/exporter/image_exporter.py) together with a [`ImagePostProcessor`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/image/image_processor.py).

Your task processors should be created from by [`ProcessorFactory`](https://imi-bigpciture/slidetap/slidetapa-app/slidetap/task/processors/processor_factory.py) so that the task application can create new instances when needed.
