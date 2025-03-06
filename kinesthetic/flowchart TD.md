flowchart TD
Image["Webcam Image Input"] --> YOLOv11["YOLOv11 Model<br>(INT8 Quantized)"]
YOLOv11 --> Detection["Detect Sticks & Beads"]
Detection --> Mapping["Map Beads to Columns"]
Mapping --> BeadCount["Count Beads per Column"]
BeadCount --> Calculate["Calculate Numeric Value<br>∑(BeadCount × PlaceValue)"]
Calculate --> Compare["Compare with Expected Answer"]

    Compare -->|Match| Correct["Provide Correct Feedback<br>in Sinhala"]
    Compare -->|No Match| Incorrect["Provide Incorrect Feedback<br>in Sinhala"]

    Correct --> NextQ["Generate Next Question"]
    Incorrect --> Retry["Prompt Student to Try Again"]

    style YOLOv11 fill:#bbf,stroke:#333,stroke-width:2px
    style Calculate fill:#fbb,stroke:#333,stroke-width:2px
