# Changelog

## v1.0.0 — MVP Release

Full MVP implementation of Nikon Camera Controller.

### Camera Control
- Connect/disconnect Nikon cameras via gPhoto2 over USB
- Automatic PTP agent termination on macOS
- Read and change ISO, shutter speed, aperture, exposure compensation, white balance
- Autofocus before capture (graceful fallback for manual focus)

### Image Capture
- JPEG and NEF capture support
- Timestamped filenames (`IMG_YYYYMMDD_HHMMSS.jpg`)
- File size and metadata display

### Exposure Analysis
- RGB + luminance histograms (256-bin, matplotlib PNG)
- Average brightness, overexposed/underexposed percentages, dynamic range (stops)
- Clipping warnings when overexposed or underexposed exceeds 5%

### Exposure Advisor
- Automated suggestions based on brightness and clipping analysis
- Concrete setting recommendations (e.g. "Lower ISO to 200")
- One-click Apply buttons to change camera settings from suggestions

### Capture History
- In-memory session with sequential capture IDs
- Thumbnail sidebar with click-to-review
- Restore previous session from disk (scans `data/captures/`)
- EXIF-based settings reconstruction on restore
- Re-apply camera settings from any historical capture

### UI
- Dark theme with warm charcoal palette
- Responsive layout (desktop and narrower screens)
- Shutter release icon with amber pulse animation during capture
- Loading state indicators for connect/disconnect/restore
- SVG favicon

### Quality
- 150 unit and integration tests
- Full mypy type checking (0 errors)
- ruff linting (0 errors)
- Google-style docstrings on all public classes and functions
