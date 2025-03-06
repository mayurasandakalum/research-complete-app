flowchart TB
subgraph "Physical Interaction"
Student[Student]
PhysicalTools["Physical Tools<br>(Abacus/Analog Clock)"]
Webcam[Webcam]
end

    subgraph "AI Processing Modules"
        YOLOv11["Abacus Detection Module<br>(YOLOv11)"]
        STN["Spatial Transformer<br>Network"]
        ResNet50["Clock Recognition<br>(ResNet50)"]
    end

    subgraph "Learning System"
        QuestionGen["Question Generator<br>(Sinhala)"]
        FeedbackEngine["Feedback Engine<br>(Sinhala)"]
        ProgressTracker["Progress Tracker"]
    end

    Student --> PhysicalTools
    PhysicalTools --> Webcam
    Webcam --> YOLOv11
    Webcam --> STN
    STN --> ResNet50

    YOLOv11 --> FeedbackEngine
    ResNet50 --> FeedbackEngine

    QuestionGen --> Student
    FeedbackEngine --> Student
    FeedbackEngine --> ProgressTracker
    ProgressTracker --> QuestionGen

    style Student fill:#f9f,stroke:#333,stroke-width:2px
    style YOLOv11 fill:#bbf,stroke:#333,stroke-width:2px
    style STN fill:#bbf,stroke:#333,stroke-width:2px
    style ResNet50 fill:#bbf,stroke:#333,stroke-width:2px
    style FeedbackEngine fill:#bfb,stroke:#333,stroke-width:2px
