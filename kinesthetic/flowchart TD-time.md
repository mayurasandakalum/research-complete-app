flowchart TD
Image["Webcam Image Input"] --> Detect["Detect Clock in Frame"]
Detect --> STN["Spatial Transformer Network<br>(Mixed INT8/FP16)"]
STN --> Transform["Transform to Fronto-parallel View<br>Correct Distortion"]
Transform --> ResNet["ResNet50 Classifier<br>(720 Time Classes)"]
ResNet --> TimeClass["Identify Most Likely Time Class"]
TimeClass --> Extract["Extract Hour and Minute<br>Hour = [max_pred/60]<br>Minute = max_pred mod 60"]
Extract --> Compare["Compare with Expected Time"]

    Compare -->|Match| Correct["Provide Correct Feedback<br>in Sinhala"]
    Compare -->|No Match| Incorrect["Provide Incorrect Feedback<br>in Sinhala"]

    Correct --> NextQ["Generate Next Question"]
    Incorrect --> Retry["Prompt Student to Try Again"]

    style STN fill:#bbf,stroke:#333,stroke-width:2px
    style ResNet fill:#bbf,stroke:#333,stroke-width:2px
    style Extract fill:#fbb,stroke:#333,stroke-width:2px
