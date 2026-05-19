# MoldEZ - Professional Culture Analysis Solution (Mark IV)

MoldEZ is a desktop application for automated mold culture analysis. It uses computer vision to detect petri dishes, segment fungal colonies, and generate structured PDF reports, replacing tedious manual measurement in laboratory workflows.

Developed at Truman State University under the TruScholars Summer Undergraduate Research Program.

---

## Features

- AI-assisted petri dish detection and colony segmentation
- CLAHE image preprocessing for low-quality or variable-lighting photos
- Growth trend analysis across time-series samples
- Automated PDF report generation
- Supports JPEG, PNG, and HEIC/HEIF image formats
- Drag-and-drop image loading

## Requirements

- Python 3.9+
- Roboflow API key

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Add your Roboflow API key to a `.env` file or when prompted on first launch.

## Built With

tkinter · Roboflow · Pillow · OpenCV · NumPy · SciPy · Matplotlib · ReportLab · pillow-heif

## Authors

**Mohammed Ayan Mahmood** — Primary Developer, Dept. of Chemistry  
**Dr. Kafi R. Rahman** — Dept. of Computer and Data Sciences  
**Dr. Hajeewaka C. Mendis** — Dept. of Agricultural and Biological Sciences  

Contributors: M. Raahim, M. T. Ibn Alam, A. Bukhari, M. McGowin, H. Momeni, E. Thompson

## License

© 2026 Office of Student Research, Truman State University. See [LICENSE](LICENSE) for terms.
