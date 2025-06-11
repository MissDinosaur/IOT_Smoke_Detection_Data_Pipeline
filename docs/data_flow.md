```text
                         +-------------------------+
                         |     Batch Processing    |
                         |    (Airflow + Pandas)   |
                         +-------------------------+
                                  |
               Kaggle Data (CSV)  |
                                  v
+--------------------+     +-------------------+       +---------------------+
| Historical CSV     | --> | Model Training    |  -->  | Model.pkl           |
| (Kaggle dataset)   |     | (scikit-learn)    |       | (saved model file)  |
+--------------------+     +-------------------+       +---------------------+

                                  ▲
                                  |
        +----------------+    Simulated stream from CSV
        | Python script  | ----------------------------->
        | Kafka Producer |
        +----------------+

                                  |
                                  v
                        +---------------------+
                        | Stream Processing   |
                        | (Kafka Consumer +   |
                        |   Real-time Inference) |
                        +---------------------+

                                  |
                                  v
                      +----------------------------+
                      | Dashboard + Monitoring     |
                      | (Flask + Grafana + Prom)   |
                      +----------------------------+
```