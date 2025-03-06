flowchart TD
subgraph "Physical Interaction"
Student[Student]
PhysicalTools["Physical Tools<br>(Abacus/Analog Clock)"]
Webcam[Webcam]
end

    subgraph "Learning System"
        LessonUI["Lesson Selection UI<br>(Addition, Subtraction, Time)"]
        QuestionGen["Question Generator<br>(Sinhala)"]
        FeedbackEngine["Feedback Engine<br>(Sinhala)"]
        ProgressTracker["Progress Tracker"]
    end

    subgraph "AI Processing Modules"
        YOLOv11["Abacus Detection<br>(YOLOv11)"]
        STN["Spatial Transformer<br>Network (STN)"]
        ResNet50["Clock Recognition<br>(ResNet50)"]
    end

    %% Student selects lesson
    Student -->|Selects Lesson| LessonUI
    LessonUI -->|Addition| QuestionGen
    LessonUI -->|Subtraction| QuestionGen
    LessonUI -->|Time| QuestionGen

    %% Question generation and student interaction
    QuestionGen -->|Math Problem in Sinhala| Student
    Student -->|Solves Problem| PhysicalTools
    PhysicalTools -->|Image| Webcam

    %% Processing based on lesson type
    Webcam -->|Abacus Image| YOLOv11
    Webcam -->|Clock Image| STN
    STN -->|Aligned Image| ResNet50

    %% Feedback and progress
    YOLOv11 -->|Abacus Value| FeedbackEngine
    ResNet50 -->|Time Value| FeedbackEngine
    FeedbackEngine -->|Feedback in Sinhala| Student
    FeedbackEngine -->|Performance Data| ProgressTracker
    ProgressTracker -->|Progress Info| QuestionGen

    %% Styling for clarity
    style Student fill:#f9f,stroke:#333,stroke-width:2px
    style PhysicalTools fill:#f9f,stroke:#333,stroke-width:2px
    style Webcam fill:#f9f,stroke:#333,stroke-width:2px
    style LessonUI fill:#bfb,stroke:#333,stroke-width:2px
    style QuestionGen fill:#bfb,stroke:#333,stroke-width:2px
    style FeedbackEngine fill:#bfb,stroke:#333,stroke-width:2px
    style ProgressTracker fill:#bfb,stroke:#333,stroke-width:2px
    style YOLOv11 fill:#bbf,stroke:#333,stroke-width:2px
    style STN fill:#bbf,stroke:#333,stroke-width:2px
    style ResNet50 fill:#bbf,stroke:#333,stroke-width:2px
