# Data Directory

This folder is intended to store the dataset used in the **IoT Smoke Detection Data Pipeline** project.

---

## Dataset Not Included

To keep this repository lightweight, the actual dataset file is **not included** here.

You can download the dataset manually from Kaggle:

**[Smoke Detection Dataset on Kaggle](https://www.kaggle.com/datasets/deepcontractor/smoke-detection-dataset)**

---

## Instructions

1. Go to the Kaggle dataset page linked above.
2. Download the `.csv` file (e.g., `smoke_detection_iot.csv`).
3. Place the file inside this `data/` directory.

Your project structure should look like this:
```text
iot_smoke_detection_data_pipeline/
├── data/
│ └── smoke_detection_iot.csv
```



---

## Notes

- Make sure the filename matches what your scripts expect.
- If using Docker, confirm that this folder is properly mounted as a volume if required in your `docker-compose.yml`.
- This folder is listed in `.gitignore`.

---

Once the dataset is placed here, you're ready to run batch processing and train your ML pipeline!


